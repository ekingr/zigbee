# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: zbCtrl.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0czbCtrl.proto\x12\x06zbCtrl\"\x1e\n\x0fGetStateRequest\x12\x0b\n\x03key\x18\x01 \x01(\t\"!\n\x10GetStateResponse\x12\r\n\x05state\x18\x01 \x01(\t\"-\n\x0fSetStateRequest\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05state\x18\x02 \x01(\t\"#\n\x10SetStateResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x32\x8a\x01\n\x06ZBCtrl\x12?\n\x08GetState\x12\x17.zbCtrl.GetStateRequest\x1a\x18.zbCtrl.GetStateResponse\"\x00\x12?\n\x08SetState\x12\x17.zbCtrl.SetStateRequest\x1a\x18.zbCtrl.SetStateResponse\"\x00\x42\x1dZ\x1bgit.ekin.gr/zbGateway/protob\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'zbCtrl_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'Z\033git.ekin.gr/zbGateway/proto'
  _globals['_GETSTATEREQUEST']._serialized_start=24
  _globals['_GETSTATEREQUEST']._serialized_end=54
  _globals['_GETSTATERESPONSE']._serialized_start=56
  _globals['_GETSTATERESPONSE']._serialized_end=89
  _globals['_SETSTATEREQUEST']._serialized_start=91
  _globals['_SETSTATEREQUEST']._serialized_end=136
  _globals['_SETSTATERESPONSE']._serialized_start=138
  _globals['_SETSTATERESPONSE']._serialized_end=173
  _globals['_ZBCTRL']._serialized_start=176
  _globals['_ZBCTRL']._serialized_end=314
# @@protoc_insertion_point(module_scope)
