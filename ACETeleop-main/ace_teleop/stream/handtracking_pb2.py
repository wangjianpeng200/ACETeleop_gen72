# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: handtracking.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x12handtracking.proto\x12\x0chandtracking"\xdb\x01\n\tMatrix4x4\x12\x0b\n\x03m00\x18\x01 \x01(\x02\x12\x0b\n\x03m01\x18\x02 \x01(\x02\x12\x0b\n\x03m02\x18\x03 \x01(\x02\x12\x0b\n\x03m03\x18\x04 \x01(\x02\x12\x0b\n\x03m10\x18\x05 \x01(\x02\x12\x0b\n\x03m11\x18\x06 \x01(\x02\x12\x0b\n\x03m12\x18\x07 \x01(\x02\x12\x0b\n\x03m13\x18\x08 \x01(\x02\x12\x0b\n\x03m20\x18\t \x01(\x02\x12\x0b\n\x03m21\x18\n \x01(\x02\x12\x0b\n\x03m22\x18\x0b \x01(\x02\x12\x0b\n\x03m23\x18\x0c \x01(\x02\x12\x0b\n\x03m30\x18\r \x01(\x02\x12\x0b\n\x03m31\x18\x0e \x01(\x02\x12\x0b\n\x03m32\x18\x0f \x01(\x02\x12\x0b\n\x03m33\x18\x10 \x01(\x02":\n\x08Skeleton\x12.\n\rjointMatrices\x18\x01 \x03(\x0b\x32\x17.handtracking.Matrix4x4"^\n\x04Hand\x12,\n\x0bwristMatrix\x18\x01 \x01(\x0b\x32\x17.handtracking.Matrix4x4\x12(\n\x08skeleton\x18\x02 \x01(\x0b\x32\x16.handtracking.Skeleton"\x82\x01\n\nHandUpdate\x12%\n\tleft_hand\x18\x01 \x01(\x0b\x32\x12.handtracking.Hand\x12&\n\nright_hand\x18\x02 \x01(\x0b\x32\x12.handtracking.Hand\x12%\n\x04Head\x18\x03 \x01(\x0b\x32\x17.handtracking.Matrix4x4" \n\rHandUpdateAck\x12\x0f\n\x07message\x18\x01 \x01(\t2b\n\x13HandTrackingService\x12K\n\x11StreamHandUpdates\x12\x18.handtracking.HandUpdate\x1a\x18.handtracking.HandUpdate"\x00\x30\x01\x62\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "handtracking_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals["_MATRIX4X4"]._serialized_start = 37
    _globals["_MATRIX4X4"]._serialized_end = 256
    _globals["_SKELETON"]._serialized_start = 258
    _globals["_SKELETON"]._serialized_end = 316
    _globals["_HAND"]._serialized_start = 318
    _globals["_HAND"]._serialized_end = 412
    _globals["_HANDUPDATE"]._serialized_start = 415
    _globals["_HANDUPDATE"]._serialized_end = 545
    _globals["_HANDUPDATEACK"]._serialized_start = 547
    _globals["_HANDUPDATEACK"]._serialized_end = 579
    _globals["_HANDTRACKINGSERVICE"]._serialized_start = 581
    _globals["_HANDTRACKINGSERVICE"]._serialized_end = 679
# @@protoc_insertion_point(module_scope)
