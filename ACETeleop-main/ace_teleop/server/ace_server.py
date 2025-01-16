import cv2
import time
import multiprocessing

import numpy as np
import transforms3d.euler as euler

from multiprocessing import Queue, Event
from ace_teleop.configs.server.ace_const import *
from ace_teleop.server.utils import *
from ace_teleop.server.server import Server
from ace_teleop.server.agent_process import AgentProcess
from ace_teleop.utils.initializer import ACEInitializer

multiprocessing.set_start_method("fork")

class ACEServer(Server):
    def __init__(self, cfg: dict, debug: bool = False, print_freq: bool = False) -> None:
        
        self.debug = debug
        self.initializer = ACEInitializer()   #初始化器，用于初始化手腕数据，包括运动位置限制和手腕姿态

        self.initialized = debug
        self.start = debug

        self.print_freq = print_freq

        self.mode = cfg["mode"]

        agent_cfg = {}
        self.enable_agent = {}   #有无当前手臂config文件
        self.process_event = {}
        self.queue = {}
        self.process = {}
        self.wrist = {}
        for name in ["left", "right"]:
            agent_cfg[name] = cfg.get(f"{name}_agent", None)

            self.enable_agent[name] = agent_cfg[name] is not None

            if not self.enable_agent[name]:
                self.initialized = True
                print("Single agent mode do not support auto initialization")

            if self.enable_agent[name]:
                self.process_event[name] = Event()
                #使用进程间的通信，获取其他进程写入的数据
                self.queue[name] = Queue()
                self.process[name] = AgentProcess(
                    self.mode,
                    agent_cfg[name],
                    name,
                    self.process_event[name],
                    self.queue[name],
                )    #创建进程,dy电机生成末端位姿 齐次矩阵
                self.process[name].start()

            self.wrist[name] = None

        if not self.enable_agent["left"] and not self.enable_agent["right"]:    #双臂都不存在
            raise ValueError("No agent is enabled")

        self.cfg = cfg
        self.init_cfg()
        self.init_server()
        self.init_viewer()
        self.init_mapping()

        if self.print_freq:
            self.init_fps()

    #可视化配置，目前感觉有问题
    def init_viewer(self) -> None:
        if self.debug:
            for name in ["left", "right"]:
                if self.enable_agent[name]:
                    cv2.namedWindow(f"Webcam {name}", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(f"Webcam {name}", 640, 480)
        else:
            cv2.namedWindow("Mapping", cv2.WINDOW_NORMAL)

    #初始化映射，读取配置文件，
    def init_mapping(self) -> None:

        self.is_map_rot = False
        self.lock_x = False
        self.lock_y = False
        self.lock_z = False
        self.is_static = False
        self.static = {}
        self.x, self.y, self.z = {}, {}, {}

        self.mapping_center, self.offset, self.center, self.wrist_init = {}, {}, {}, {}
        for name in ["left", "right"]:
            if self.enable_agent[name]:
                self.mapping_center[name] = self.wrist_init_pos[name]
                self.offset[name] = [0, 0, 0]
                self.center[name] = None

                self.wrist_init[name] = R_map(
                    self.wrist_init_rot[name],
                    np.eye(4),
                    self.roll_scale,
                    self.pitch_scale,
                    self.yaw_scale,  #--------------------------------------------------------------------------------
                    self.roll_limit,
                    self.pitch_limit,
                    self.yaw_limit,
                )

        self.smooth = 100
        self.smooth_step = 100
        self.warming = 100
        self.warming_step = 100

    def init_fps(self) -> None:
        self.time = time.perf_counter()
        self.totalfps = 0
        self.totaltime = 0

    def run(self) -> None:
        #机械臂的位置、帧数据、目标矩阵和上一次的手腕位置
        joint_pos, frame, target_matrix, last_wrist = {}, {}, {}, {}

        while True:
            # 打印帧率
            if self.print_freq:
                tac = time.perf_counter()
                fps = 1 / (tac - self.time)
                if fps < 40:
                    self.totalfps += fps
                    self.totaltime += 1
                    print(self.totalfps / self.totaltime)
                self.time = tac

            for name in ["left", "right"]:
                if self.enable_agent[name]:
                    self.process_event[name].set()    #设置事件

            for name in ["left", "right"]:
                if self.enable_agent[name]:
                    self.wrist[name], joint_pos[name], frame[name] = self.queue[
                        name
                    ].get()  #获取进程中的数据
                    target_matrix[name] = self.map_rot(name)  #目标

            if self.smooth_step < self.smooth:
                alpha = self.smooth_step / self.smooth

                for name in ["left", "right"]:
                    if self.enable_agent[name]:
                        target_matrix[name] = smooth_rot(
                            last_wrist[name][:3, :3], target_matrix[name], alpha
                        )
                        self.wrist[name][:3, :3] = target_matrix[name]

                # print(f"Transition step {self.smooth_step}, alpha {alpha:.2f}")
                self.smooth_step += 1

            else:
                for name in ["left", "right"]:
                    if self.enable_agent[name]:
                        self.wrist[name][:3, :3] = target_matrix[name]

            key = cv2.waitKey(1) & 0xFF

            #已经被初始化，单臂模式或者双臂已初始化
            if self.initialized:
                if not self.start:
                    for name in ["left", "right"]:
                        if self.enable_agent[name]:
                            self.offset[name] = get_mapping_offset(
                                self.mapping_center[name],
                                self.wrist[name][:3, 3],
                                self.pos_scale,
                            )
                            print(f"MAP TO INIT POS for {name} agent")
                            self.wrist_init[name].init_rot = self.wrist[name][
                                :3, :3
                            ].copy()
                            print(f"START MAP ROT for {name} agent")
                    self.is_map_rot = True    #开始映射旋转
                    self.start = True
                    self.warming_step = 0
                    print("Initialization complete")
                elif key == ord("r"):
                    if not self.is_map_rot:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.wrist_init[name].init_rot = self.wrist[name][
                                    :3, :3
                                ].copy()
                                print(f"START MAP ROT for {name} agent")
                        self.is_map_rot = True
                    else:
                        self.is_map_rot = False
                        print("STOP MAP ROT")
                    self.smooth_step = 0

                elif key == ord("p"):
                    if not self.is_static:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.offset[name] = get_mapping_offset(
                                    self.mapping_center[name],
                                    self.wrist[name][:3, 3],
                                    self.pos_scale,
                                )
                                print(f"MAP TO INIT POS for {name} agent")
                        self.smooth_step = 0
                        if not self.start:
                            for name in ["left", "right"]:
                                if self.enable_agent[name]:
                                    self.wrist_init[name].init_rot = self.wrist[name][
                                        :3, :3
                                    ].copy()
                                    print(f"START MAP ROT for {name} agent")
                                    self.is_map_rot = True
                            self.start = True
                            self.warming_step = 0
                            print("Initialization complete")
                    else:
                        print("STATIC MODE, cannot change position")
                elif key == ord("m"):
                    if not self.is_static:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.static[name] = self.wrist[name].copy()
                                self.center[name] = (
                                    self.wrist[name][:3, 3] * self.pos_scale
                                    + self.offset[name]
                                )
                                print(f"SET STATIC MODE for {name} agent")
                        self.is_static = True
                    else:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.offset[name] = get_mapping_offset(
                                    self.center[name],
                                    self.wrist[name][:3, 3],
                                    self.pos_scale,
                                )
                        self.smooth_step = 0
                        self.is_static = False
                        print("START MOVING")
                elif key == ord("x"):
                    if not self.lock_x:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.x[name] = self.wrist[name][0, 3]
                                print(f"LOCK X for {name} agent")
                        self.lock_x = True
                    else:
                        self.lock_x = False
                        self.smooth_step = 0
                        print("UNLOCK X")
                elif key == ord("y"):
                    if not self.lock_y:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.y[name] = self.wrist[name][1, 3]
                                print(f"LOCK Y for {name} agent")
                        self.lock_y = True
                    else:
                        self.lock_y = False
                        self.smooth_step = 0
                        print("UNLOCK Y")
                elif key == ord("z"):
                    if not self.lock_z:
                        for name in ["left", "right"]:
                            if self.enable_agent[name]:
                                self.z[name] = self.wrist[name][2, 3]
                                print(f"LOCK Z for {name} agent")
                        self.lock_z = True
                    else:
                        self.lock_z = False
                        self.smooth_step = 0
                        print("UNLOCK Z")
                elif key == ord("q"):
                    exit()

            for name in ["left", "right"]:
                if self.is_static:
                    if self.enable_agent[name]:
                        self.wrist[name][:3, 3] = self.static[name].copy()[:3, 3]

                if self.lock_z:
                    if self.enable_agent[name]:
                        self.wrist[name][2, 3] = self.z[name]
                if self.lock_x:
                    if self.enable_agent[name]:
                        self.wrist[name][0, 3] = self.x[name]
                if self.lock_y:
                    if self.enable_agent[name]:
                        self.wrist[name][1, 3] = self.y[name]

                if self.enable_agent[name]:
                    self.wrist[name][:3, 3] *= self.pos_scale
                    self.wrist[name][:3, 3] += self.offset[name]

                if self.smooth_step < self.smooth:
                    alpha = self.smooth_step / self.smooth
                    if self.enable_agent[name]:
                        self.wrist[name][:3, 3] = smooth_pos(last_wrist[name][:3, 3], self.wrist[name][:3, 3], alpha)
                        print(f"Smoothing:{alpha:.2f}")
                        self.smooth_step += 1

                if self.enable_agent[name]:
                    last_wrist[name] = self.wrist[name]
                    if self.mode == "mirror":
                        self.wrist[name] = np.dot(MIRROR, self.wrist[name])  #做镜像处理

                    self.wrist[name][:3, 3] = clamp_point_to_sphere(
                        self.wrist[name][:3, 3],
                        self.center_l[name],    #球体的中心坐标
                        self.radius_l[name],    #球体的半径
                    )   #将坐标一个点限制在一个球体内

                    #这段代码的作用是将 self.wrist[name][2, 3] 的值限制在 0 到 0.3 之间。np.clip 是 NumPy 库中的一个函数，用于将数组中的值限制在指定的范围内。
                    self.wrist[name][2, 3] = np.clip(self.wrist[name][2, 3], 0, 0.2)      #限制z轴的值在0到0.3之间

                    #! need to fix
                    if (not self.initialized or not self.start) or (
                        self.warming_step < self.warming
                    ):
                        self.wrist[name][:3, :3] = self.wrist_init_rot[name]
                        self.wrist[name][:3, 3] = self.wrist_init_pos[name]
                        if self.mode == "mirror":
                            self.wrist[name] = np.dot(MIRROR, self.wrist[name])
                        if self.warming_step < self.warming:
                            self.warming_step += 1
                            print(f"Warming:{self.warming_step/self.warming:.2f}")


# 这段代码的作用是对 self.wrist[name] 进行两次矩阵乘法操作，分别是 R_z_90_ccw_pose 和 YUP2ZUP_INV_2D。

# if self.is_ACE:: 这是一个条件判断语句，检查 self.is_ACE 是否为 True。如果是，则执行下面的代码块。

# self.wrist[name] = np.dot(R_z_90_ccw_pose, self.wrist[name]): 这行代码将 self.wrist[name] 与 R_z_90_ccw_pose 进行矩阵乘法操作，并将结果重新赋值给 self.wrist[name]。R_z_90_ccw_pose 可能是一个表示绕 Z 轴逆时针旋转 90 度的旋转矩阵。

# self.wrist[name] = np.dot(YUP2ZUP_INV_2D, self.wrist[name]): 这行代码将 self.wrist[name] 与 YUP2ZUP_INV_2D 进行矩阵乘法操作，并将结果重新赋值给 self.wrist[name]。YUP2ZUP_INV_2D 可能是一个将 Y 轴向上的坐标系转换为 Z 轴向上的坐标系的变换矩阵。

# 总的来说，这段代码的作用是对 self.wrist[name] 进行两次矩阵乘法操作，分别是绕 Z 轴逆时针旋转 90 度和将 Y 轴向上的坐标系转换为 Z 轴向上的坐标系。

                    if self.is_ACE:
                        print("变化前")
                        print(f"腕部数据（{name}): {self.wrist[name]}")
                        self.wrist[name] = np.dot(R_z_90_ccw_pose, self.wrist[name])
                        print("变化中")
                        print(f"腕部数据（{name}): {self.wrist[name]}")
                    self.wrist[name] = np.dot(YUP2ZUP_INV_2D, self.wrist[name])
                    print("变化后")
                    print(f"腕部数据（{name}): {self.wrist[name]}")


                    if name == "left":
                        if self.mode == "mirror":
                            self.servicer.matrix_right = self.wrist[name]
                        else:
                            self.servicer.matrix_left = self.wrist[name]    #将左手腕的姿态矩阵存储在 servicer 的 matrix_left 属性中

                        if joint_pos[name] is not None:  #手指关节角度
                            if self.mode == "mirror":
                                self.servicer.points_right[indices1] = (
                                    np.array([1, 1, -1]) * joint_pos[name][indices2]
                                )
                                self.servicer.points_right[0] = [0, 0, 0]
                            else:
                                self.servicer.points_left[indices1] = joint_pos[name][
                                    indices2
                                ]
                                self.servicer.points_left[0] = [0, 0, 0]  # for point 0

                    elif name == "right":
                        if self.mode == "mirror":
                            self.servicer.matrix_left = self.wrist[name]
                        else:
                            self.servicer.matrix_right = self.wrist[name]

                        if joint_pos[name] is not None:
                            if self.mode == "mirror":
                                self.servicer.points_left[indices1] = (
                                    np.array([1, 1, -1]) * joint_pos[name][indices2]
                                )
                                self.servicer.points_left[0] = [0, 0, 0]
                            else:
                                self.servicer.points_right[indices1] = joint_pos[name][
                                    indices2
                                ]
                                self.servicer.points_right[0] = [0, 0, 0]  # for point 0

                    if self.debug:
                        cv2.imshow(f"Webcam {name}", frame[name])
            #如果左右手臂都存在，并且没有被初始化，，并且检测到了手指数据，则将当前手腕数据用于初始化
            if self.enable_agent["left"] and self.enable_agent["right"]:
                if (
                    not self.initialized
                    and joint_pos["left"] is not None
                    and joint_pos["right"] is not None
                ):
                    data = (
                        self.wrist["left"],
                        self.wrist["right"],
                        joint_pos["left"],
                        joint_pos["right"],
                    )
                    self.initialized = self.initializer.init(*data)

            self.servicer.update_event.set()

    def map_rot(self, wrist_id) -> np.ndarray:
            """
            计算目标旋转矩阵。

            该方法根据当前手腕姿态和初始化的手腕姿态，计算目标旋转矩阵。

            参数:
            - wrist_id: 手腕的标识符，用于区分左右手腕。

            返回:
            计算得到的目标旋转矩阵。
            """
            # 获取当前手腕的姿态
            wrist = self.wrist[wrist_id]
            # 获取初始化的手腕姿态
            wrist_init = self.wrist_init[wrist_id]

            # 如果启用了映射旋转
            if self.is_map_rot:
                # 计算当前手腕姿态相对于初始化姿态的旋转矩阵
                R_delta = wrist[:3, :3] @ np.linalg.inv(wrist_init.init_rot)
                # 将旋转矩阵转换为欧拉角
                roll_delta, pitch_delta, yaw_delta = euler.mat2euler(R_delta, axes="sxyz")

                # 根据缩放因子和偏移量调整滚动角
                roll_delta_ = roll_delta * wrist_init.roll_scale
                roll_delta_ += np.deg2rad(self.roll_offset)
                roll_delta_ = np.clip(
                    roll_delta_, wrist_init.roll_limit[0], wrist_init.roll_limit[1]
                )

                # 根据缩放因子和限制调整俯仰角
                pitch_delta_ = pitch_delta * wrist_init.pitch_scale
                pitch_delta_ = np.clip(
                    pitch_delta_, wrist_init.pitch_limit[0], wrist_init.pitch_limit[1]
                )

                # 根据缩放因子和限制调整偏航角
                yaw_delta_ = yaw_delta * wrist_init.yaw_scale
                yaw_delta_ = np.clip(
                    yaw_delta_, wrist_init.yaw_limit[0], wrist_init.yaw_limit[1]
                )

                # 如果模式为镜像，反转滚动角和偏航角
                if self.mode == "mirror":
                    roll_delta_ = -roll_delta_
                    yaw_delta_ = -yaw_delta_

                # 将欧拉角转换为度
                roll_delta_ = np.rad2deg(roll_delta_)
                pitch_delta_ = np.rad2deg(pitch_delta_)
                yaw_delta_ = np.rad2deg(yaw_delta_)

                # 打印调整后的欧拉角
                # print(f"Roll: {roll_delta_:.2f}, Pitch: {pitch_delta_:.2f}, Yaw: {yaw_delta_:.2f}")

                # 将调整后的欧拉角转换为旋转矩阵
                wrist_delta = euler_to_matrix(roll_delta_, pitch_delta_, yaw_delta_)
                # 计算目标旋转矩阵
                target_matrix = wrist_delta @ wrist_init.mapping_rot

            # 如果未启用映射旋转，直接使用当前手腕姿态
            else:
                target_matrix = wrist[:3, :3]

            # 返回目标旋转矩阵
            return target_matrix