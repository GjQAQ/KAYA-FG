import contextlib
from ctypes import *
import dataclasses
from enum import Flag, Enum

from .base import *

__all__ = [
    'close_frame_grabber',
    'connect_frame_grabber',
    'get_frame_grabber_info',
    'get_grabber_value',
    'open_frame_grabber',
    'scan_frame_grabber',
    'set_grabber_value',
]

INVALID_FGHANDLE = 4294967295  # legacy code


def scan_frame_grabber():
    if not isinstance(kydll, CDLL):
        return None

    # Retrieve the number of devices
    dev_num = c_uint(0)
    s = kydll.KY_DeviceScan(byref(dev_num))

    return dev_num.value


def get_frame_grabber_info(index: int):
    di_pointer = POINTER(CDeviceInfo)
    c_info = CDeviceInfo()
    kydll.KY_DeviceInfo.argtypes = (c_int, di_pointer)
    kydll.KY_DeviceInfo.restype = c_uint32
    s = kydll.KY_DeviceInfo(index, byref(c_info))
    if s != FGSTATUS_OK:
        return None

    info = FrameGrabberInfo(
        c_info.version,
        c_info.szDeviceDisplayName.decode(),
        c_info.nBus,
        c_info.nSlot,
        c_info.nFunction,
        c_info.DevicePID,
        c_info.isVirtual,
        DeviceInfoFlags(c_info.m_Flags).value,  # noqa
        DeviceProtocol(c_info.m_Protocol).value,
        c_info.DeviceGeneration,
    )
    return info


def open_frame_grabber(index: int):
    if not isinstance(index, int):
        raise TypeError('index must be an integer')

    kydll.KYFG_Open.argtypes = (c_int,)
    kydll.KYFG_Open.restype = c_uint32
    handle: int = kydll.KYFG_Open(index)

    if handle == INVALID_FGHANDLE:
        raise KYException('Got invalid frame grabber handle')
    return handle


def close_frame_grabber(fg_handle: int = 0):
    if not isinstance(fg_handle, int):
        raise TypeError('fg_handle must be an integer')

    kydll.KYFG_Close.argtypes = (c_uint,)
    kydll.KYFG_Close.restype = c_uint32
    fg_handle = int(fg_handle)
    s = kydll.KYFG_Close(fg_handle)


@contextlib.contextmanager
def connect_frame_grabber(index: int):
    handle = open_frame_grabber(index)
    try:
        yield handle
    finally:
        close_frame_grabber(handle)


# @formatter:off
class DeviceInfoFlags(Flag):
    EMPTY       = 0x0
    GRABBER     = 0x1
    GENERATOR   = 0x2
    MIXER       = 0x4


class DeviceProtocol(Enum):
    CXP     = 0x0
    CLHS    = 0x1
    GIGE    = 0x2
    MIXED   = 0xFF
    UNKNOWN = 0xFFFF


@dataclasses.dataclass
class FrameGrabberInfo:
    version:                int = 0
    sz_device_display_name: str = ""
    n_bus:                  int = 0
    n_slot:                 int = 0
    n_function:             int = 0
    device_pid:             int = 0
    is_virtual:             int = 0
    flags:                  int = DeviceInfoFlags.EMPTY
    protocol:               int = DeviceProtocol.UNKNOWN
    device_generation:      int = 0


class CDeviceInfo(Structure):
    _pack_ = 1
    _fields_ = [
        ("version",             c_uint32),
        ("szDeviceDisplayName", DevNameStr),
        ("nBus",                c_int),
        ("nSlot",               c_int),
        ("nFunction",           c_int),
        ("DevicePID",           c_uint32),
        ("isVirtual",           c_byte),
        ("m_Flags",             c_byte),
        ("m_Protocol",          c_uint),
        ("DeviceGeneration",    c_uint32),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = 4
# @formatter:on


def get_grabber_value_type(handle, param):
    kydll.KYFG_GetGrabberValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueType.restype = c_int32

    param_str_buf = create_string_buffer(bytes(param.encode()))

    grabber_value_type = kydll.KYFG_GetGrabberValueType(handle, param_str_buf)
    return grabber_value_type


def get_grabber_value(handle, param):
    kydll.KYFG_GetGrabberValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueType.restype = c_int32
    (status, valueType) = get_grabber_value_type(handle, param)

    if valueType == PropType.INT:
        return kyfg_get_grabber_value_int(handle, param)
    elif valueType == PropType.ENUM:
        enum_int = kyfg_get_grabber_value_enum(handle, param)
        enum_str = kyfg_get_grabber_value_string_copy(handle, param)
        return enum_int, enum_str
    elif valueType == PropType.BOOL:
        return kyfg_get_grabber_value_bool(handle, param)
    elif valueType == PropType.FLOAT:
        return kyfg_get_grabber_value_float(handle, param)
    elif valueType == PropType.STRING:
        return kyfg_get_grabber_value_string_copy(handle, param)
    elif valueType == PropType.COMMAND:
        command_executed = c_ubyte(0)
        kydll.KYFG_GetGrabberValue.argtypes = (c_uint, c_char_p, c_void_p)
        kydll.KYFG_GetGrabberValue.restype = c_uint32
        param_str_buf = create_string_buffer(bytes(param.encode()))
        s = kydll.KYFG_GetGrabberValue(handle, param_str_buf, byref(command_executed))
        return bool(command_executed.value)
    return None


def kyfg_get_grabber_value_int(handle, param):
    kydll.KYFG_GetGrabberValueInt.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueInt.restype = c_int64
    param_str_buf = create_string_buffer(bytes(param.encode()))

    grabber_value_int = c_int64(0)

    s = kydll.KYFG_GetGrabberValue(handle, param_str_buf, byref(grabber_value_int))

    return grabber_value_int.value


def kyfg_get_grabber_value_float(handle, param):
    kydll.KYFG_GetGrabberValueFloat.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueFloat.restype = c_double

    param_str_buf = create_string_buffer(bytes(param.encode()))

    grabber_value_float = c_double(0)

    s = kydll.KYFG_GetGrabberValue(handle, param_str_buf, byref(grabber_value_float))

    return grabber_value_float.value


def kyfg_get_grabber_value_bool(handle, param):
    kydll.KYFG_GetGrabberValueBool.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueBool.restype = c_ubyte

    param_str_buf = create_string_buffer(bytes(param.encode()))
    grabber_value_bool = c_ubyte(0)

    s = kydll.KYFG_GetGrabberValue(handle, param_str_buf, byref(grabber_value_bool))

    return bool(grabber_value_bool.value)


def kyfg_get_grabber_value_enum(handle, param):
    kydll.KYFG_GetGrabberValueEnum.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueEnum.restype = c_int64

    paramName_str_buf = create_string_buffer(bytes(param.encode()))

    grabber_value_enum = c_int64(0)

    s = kydll.KYFG_GetGrabberValue(handle, paramName_str_buf, byref(grabber_value_enum))

    return grabber_value_enum.value


def kyfg_get_grabber_value_string_copy(handle, param):
    kydll.KYFG_GetGrabberValueStringCopy.argtypes = (c_uint, c_char_p, c_char_p, POINTER(c_uint))
    kydll.KYFG_GetGrabberValueStringCopy.restype = c_uint32

    param_name_str_buf = create_string_buffer(bytes(param.encode()))

    # Get the required size of the string
    str_size = c_uint(0)
    s = kydll.KYFG_GetGrabberValueStringCopy(handle, param_name_str_buf, None, byref(str_size))
    # Create a new string of an appropriate size
    param_value_c_string = create_string_buffer(str_size.value)
    # Fill the string with the data
    s = kydll.KYFG_GetGrabberValueStringCopy(handle, param_name_str_buf, param_value_c_string, byref(str_size))
    param_str = string_at(param_value_c_string)
    return param_str.decode()


def set_grabber_value(handle, param, value):
    kydll.KYFG_GetGrabberValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetGrabberValueType.restype = c_int32

    (status, value_type) = get_grabber_value_type(handle, param)
    if value_type == PropType.INT:
        if not isinstance(value, int):
            raise TypeError()
        return kyfg_set_grabber_value_int(handle, param, value)
    elif value_type == PropType.ENUM:
        if not isinstance(value, (int, str)):
            raise TypeError()
        if isinstance(value, str):
            return kyfg_set_grabber_value_enum_by_value_name(handle, param, value)
        else:
            return kyfg_set_grabber_value_enum(handle, param, value)
    elif value_type == PropType.BOOL:
        if not isinstance(value, bool):
            raise TypeError()
        return kyfg_set_grabber_value_bool(handle, param, value)
    elif value_type == PropType.FLOAT:
        if not isinstance(value, float):
            raise TypeError()
        return kyfg_set_grabber_value_float(handle, param, value)
    elif value_type == PropType.STRING:
        if not isinstance(value, str):
            raise TypeError()
        return kyfg_set_grabber_value_string(handle, param, value)
    elif value_type == PropType.COMMAND:
        if not isinstance(value, int):
            raise TypeError()
        param_str_buf = create_string_buffer(bytes(param.encode()))
        value_p = c_int(value)
        kydll.KYFG_SetGrabberValue.argtypes = (c_uint, c_char_p, c_void_p)
        kydll.KYFG_SetGrabberValue.restype = c_uint32
        s = kydll.KYFG_SetGrabberValue(handle, param_str_buf, byref(value_p))
    return None


def kyfg_set_grabber_value_int(handle, param, value):
    kydll.KYFG_SetGrabberValueInt.argtypes = (c_uint, c_char_p, c_int64)
    kydll.KYFG_SetGrabberValueInt.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))
    value_p = c_int64(value)
    s = kydll.KYFG_SetGrabberValueInt(handle, param_str_buf, value_p)


def kyfg_set_grabber_value_float(handle, param, value):
    kydll.KYFG_SetGrabberValueFloat.argtypes = (c_uint, c_char_p, c_double)
    kydll.KYFG_SetGrabberValueFloat.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))
    c_param_double_value = c_double(value)
    s = kydll.KYFG_SetGrabberValueFloat(handle, param_str_buf, c_param_double_value)


def kyfg_set_grabber_value_bool(handle, param, value):
    value_num = int(bool(value))
    value_c_style = c_ubyte(value_num)

    kydll.KYFG_SetGrabberValueBool.argtypes = (c_uint, c_char_p, c_ubyte)
    kydll.KYFG_SetGrabberValueBool.restype = c_uint32

    param_str_buf = create_string_buffer(bytes(param.encode()))
    s = kydll.KYFG_SetGrabberValueBool(handle, param_str_buf, value_c_style)


def kyfg_set_grabber_value_string(handle, param, value):
    kydll.KYFG_SetGrabberValueString.argtypes = (c_uint, c_char_p, c_char_p)
    kydll.KYFG_SetGrabberValueString.restype = c_uint32

    param_str_buf = create_string_buffer(bytes(param.encode()))
    value_str_buf = create_string_buffer(bytes(value.encode()))

    s = kydll.KYFG_SetGrabberValueString(handle, param_str_buf, value_str_buf)


def kyfg_set_grabber_value_enum(handle, param, value):
    value_c_style = c_int64(value)

    kydll.KYFG_SetGrabberValueEnum.argtypes = (c_uint, c_char_p, c_int64)
    kydll.KYFG_SetGrabberValueEnum.restype = c_uint32

    param_str_buf = create_string_buffer(bytes(param.encode()))
    s = kydll.KYFG_SetGrabberValueEnum(handle, param_str_buf, value_c_style)


def kyfg_set_grabber_value_enum_by_value_name(handle, param, valueName):
    kydll.KYFG_SetGrabberValueEnum_ByValueName.argtypes = (c_uint, c_char_p, c_char_p)
    kydll.KYFG_SetGrabberValueEnum_ByValueName.restype = c_uint32

    param_str_buf = create_string_buffer(bytes(param.encode()))
    value_str_buf = create_string_buffer(bytes(valueName.encode()))

    s = kydll.KYFG_SetGrabberValueEnum_ByValueName(handle, param_str_buf, value_str_buf)
