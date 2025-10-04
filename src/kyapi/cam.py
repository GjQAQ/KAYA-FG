import contextlib
from ctypes import *
import dataclasses
from ctypes import c_uint, c_uint32

from .base import *

__all__ = [
    'close_camera',
    'connect_camera',
    'get_camera_handles',
    'get_cam_info',
    'get_camera_feature',
    'open_camera',
    'set_camera_feature',
    'start_acquisition',
    'stop_acquisition',
]

MAX_CAMERAS = 16


def get_camera_handles(fg_handle: int):
    if not isinstance(fg_handle, int):
        raise TypeError('fg_handle must be an integer')

    fg_handle = int(fg_handle)
    detected_cameras_c_int32 = c_int32(MAX_CAMERAS)
    detectedCameras_c_int32_p = pointer(detected_cameras_c_int32)
    temp_arr = (c_uint * MAX_CAMERAS)(0)  # noqa
    cam_handle_array_c_uint32_p = pointer(temp_arr)
    s = kydll.KYFG_UpdateCameraList(fg_handle, cam_handle_array_c_uint32_p, detectedCameras_c_int32_p)

    cam_handles = [temp_arr[i] for i in range(detected_cameras_c_int32.value)]
    return cam_handles


def open_camera(cam_handle: int, xml_file_path: str = None):
    if not isinstance(cam_handle, int):
        raise TypeError('cam_handle must be an integer')

    cam_handle = int(cam_handle)
    if xml_file_path is not None and not isinstance(xml_file_path, str):
        raise TypeError('xml_file_path must be a string')

    kydll.KYFG_CameraOpen2.argtypes = (c_uint, c_char_p)
    kydll.KYFG_CameraOpen2.restype = c_uint32
    if xml_file_path is not None:
        xml_file_path_str_buf = create_string_buffer(bytes(xml_file_path.encode()))
    else:
        xml_file_path_str_buf = c_char_p(xml_file_path)
    s = kydll.KYFG_CameraOpen2(cam_handle, xml_file_path_str_buf)


def close_camera(cam_handle: int):
    if not isinstance(cam_handle, int):
        raise TypeError('cam_handle must be an integer')

    cam_handle = int(cam_handle)
    kydll.KYFG_CameraClose.argtypes = (c_uint,)
    kydll.KYFG_CameraClose.restype = c_uint32
    s = kydll.KYFG_CameraClose(cam_handle)


@contextlib.contextmanager
def connect_camera(fg_handle: int, cam_idx: int = 0):
    cam_handles = get_camera_handles(fg_handle)
    if len(cam_handles) != 1:
        raise RuntimeError(f'Exactly one available camera expected, got {len(cam_handles)}')

    cam_handle = cam_handles[cam_idx]
    open_camera(cam_handle)

    try:
        yield cam_handle
    finally:
        close_camera(cam_handle)


MAX_CAMERA_INFO_STRING_SIZE = 64
CAMERA_INFO2_ARRAY = c_char * (MAX_CAMERA_INFO_STRING_SIZE + 1)  # noqa


# @formatter:off
class CCameraInfo2(Structure):
    _pack_ = 1
    _fields_ = [
        ("version",                 c_int),
        ("master_link",             c_ubyte),
        ("link_mask",               c_ubyte),
        ("link_speed",              c_int),
        ("stream_id",               c_uint),
        ("deviceVersion",           CAMERA_INFO2_ARRAY),
        ("deviceVendorName",        CAMERA_INFO2_ARRAY),
        ("deviceManufacturerInfo",  CAMERA_INFO2_ARRAY),
        ("deviceModelName",         CAMERA_INFO2_ARRAY),
        ("deviceID",                CAMERA_INFO2_ARRAY),
        ("deviceUserID",            CAMERA_INFO2_ARRAY),
        ("outputCamera",            c_bool),
        ("virtualCamera",           c_bool),
        ("deviceFirmwareVersion",   CAMERA_INFO2_ARRAY),
    ]


@dataclasses.dataclass
class CameraInfo:
    version                 : int   = 1
    master_link             : int   = 0
    link_mask               : int   = 0
    link_speed              : int   = 0
    stream_id               : int   = 0
    deviceVersion           : str   = ""
    deviceVendorName        : str   = ""
    deviceManufacturerInfo  : str   = ""
    deviceModelName         : str   = ""
    deviceID                : str   = ""
    deviceUserID            : str   = ""
    outputCamera            : bool  = False
    virtualCamera           : bool  = False
    deviceFirmwareVersion   : str   = ""
# @formatter:on


def get_cam_info(cam_handle: int):
    KYFGCAMERA_INFO2_C_STYLE_POINTER = POINTER(CCameraInfo2)
    cam_info = CCameraInfo2()
    cam_info.version = 1
    kydll.KYFG_CameraInfo2.argtypes = (c_uint, KYFGCAMERA_INFO2_C_STYLE_POINTER)
    kydll.KYFG_CameraInfo2.restype = c_uint32
    s = kydll.KYFG_CameraInfo2(cam_handle, byref(cam_info))

    camInfo = CameraInfo(
        cam_info.version,
        cam_info.master_link,
        cam_info.link_mask,
        cam_info.link_speed,
        cam_info.stream_id,
        cam_info.deviceVersion.decode(),
        cam_info.deviceVendorName.decode(),
        cam_info.deviceManufacturerInfo.decode(),
        cam_info.deviceModelName.decode(),
        cam_info.deviceID.decode(),
        cam_info.deviceUserID.decode(),
        cam_info.outputCamera,
        cam_info.virtualCamera,
        cam_info.deviceFirmwareVersion.decode(),
    )
    return camInfo


def get_camera_value_type(cam_handle: int, param: str):
    kydll.KYFG_GetCameraValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueType.restype = c_int
    param_name_str_buf = create_string_buffer(bytes(param.encode()))
    cam_value_type = kydll.KYFG_GetCameraValueType(cam_handle, param_name_str_buf)
    return cam_value_type


def kyfg_get_camera_value_int(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValueInt.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueInt.restype = c_int64
    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))
    cam_value_int = c_int64(0)
    s = kydll.KYFG_GetCameraValue(cam_handle, param_name_str_buf, byref(cam_value_int))
    return cam_value_int.value


def kyfg_get_camera_value_bool(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValueBool.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueBool.restype = c_ubyte
    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))
    cam_value_bool = c_ubyte(0)
    s = kydll.KYFG_GetCameraValue(cam_handle, param_name_str_buf, byref(cam_value_bool))

    return bool(cam_value_bool.value)


def kyfg_get_camera_value_string_copy(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValueStringCopy.argtypes = (c_uint, c_char_p, c_char_p, POINTER(c_uint))
    kydll.KYFG_GetCameraValueStringCopy.restype = c_uint32

    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))

    # Get the required size of the string
    str_size = c_uint(0)
    s = kydll.KYFG_GetCameraValueStringCopy(cam_handle, param_name_str_buf, None, byref(str_size))
    # Create a new string of an appropriate size
    param_value_c_string = create_string_buffer(str_size.value)
    # Fill the string with the data
    s = kydll.KYFG_GetCameraValueStringCopy(cam_handle, param_name_str_buf, param_value_c_string, byref(str_size))
    paramStr = string_at(param_value_c_string)
    return paramStr.decode()


def kyfg_get_camera_value_float(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValueFloat.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueFloat.restype = c_double
    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))
    cam_value_float = c_double(0)
    s = kydll.KYFG_GetCameraValue(cam_handle, param_name_str_buf, byref(cam_value_float))
    return cam_value_float.value


def kyfg_get_camera_value_enum(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValueEnum.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueEnum.restype = c_int64
    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))
    cam_value_enum = c_int64(0)
    s = kydll.KYFG_GetCameraValue(cam_handle, param_name_str_buf, byref(cam_value_enum))
    return cam_value_enum.value


def kyfg_get_camera_value_register(cam_handle: int, param_name: str):
    kydll.KYFG_GetCameraValue.argtypes = (c_uint, c_char_p, c_void_p)
    kydll.KYFG_GetCameraValue.restype = c_uint32
    param_name_str_buf = create_string_buffer(bytes(param_name.encode()))

    # Retrieving buffer size
    buffer_size = c_uint(0)
    kydll.KYFG_GetCameraValueRegister(cam_handle, param_name_str_buf, None, byref(buffer_size))

    # Create a buffer to be filled with a relevant data
    param_value_c_buffer = create_string_buffer(buffer_size.value)

    # Get the data
    s = kydll.KYFG_GetCameraValueRegister(
        cam_handle, param_name_str_buf, byref(param_value_c_buffer), byref(buffer_size)
    )
    param_str = string_at(param_value_c_buffer, buffer_size.value)

    return buffer_size.value, bytes(param_str)


def get_camera_feature(cam_handle: int, param: str):
    cam_handle = int(cam_handle)
    kydll.KYFG_GetCameraValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueType.restype = c_int32

    paramValueType = get_camera_value_type(cam_handle, param)

    if paramValueType == PropType.INT:
        return kyfg_get_camera_value_int(cam_handle, param)
    elif paramValueType == PropType.ENUM:
        # return KYFG_GetCameraValueEnum(cam_handle, param_name)
        enum_int = kyfg_get_camera_value_enum(cam_handle, param)
        enum_str = kyfg_get_camera_value_string_copy(cam_handle, param)
        return enum_int, enum_str
    elif paramValueType == PropType.BOOL:
        return kyfg_get_camera_value_bool(cam_handle, param)
    elif paramValueType == PropType.FLOAT:
        return kyfg_get_camera_value_float(cam_handle, param)
    elif paramValueType == PropType.STRING:
        return kyfg_get_camera_value_string_copy(cam_handle, param)
    elif paramValueType == PropType.COMMAND:
        command_executed = c_ubyte(0)
        kydll.KYFG_GetCameraValue.argtypes = (c_uint, c_char_p, c_void_p)
        kydll.KYFG_GetCameraValue.restype = c_uint32
        param_name_str_buf = create_string_buffer(bytes(param.encode()))
        s = kydll.KYFG_GetCameraValue(cam_handle, param_name_str_buf, byref(command_executed))
        return bool(command_executed.value)
    elif paramValueType == PropType.REGISTER:
        size, buffer = kyfg_get_camera_value_register(cam_handle, param)
        return buffer
    return None


def set_camera_feature(cam_handle, param, value):
    kydll.KYFG_GetCameraValueType.argtypes = (c_uint, c_char_p)
    kydll.KYFG_GetCameraValueType.restype = c_int32

    paramValueType = get_camera_value_type(cam_handle, param)
    if paramValueType == PropType.INT:
        if not isinstance(value, int):
            raise TypeError()
        return kyfg_set_camera_value_int(cam_handle, param, value)
    elif paramValueType == PropType.ENUM:
        if not isinstance(value, (int, str)):
            raise TypeError()
        if isinstance(value, str):
            return kyfg_set_camera_value_enum_by_value_name(cam_handle, param, value)
        else:
            return kyfg_set_camera_value_enum(cam_handle, param, value)
    elif paramValueType == PropType.BOOL:
        if not isinstance(value, bool):
            raise TypeError()
        return kyfg_set_camera_value_bool(cam_handle, param, value)
    elif paramValueType == PropType.FLOAT:
        if not isinstance(value, float):
            raise TypeError()
        return kyfg_set_camera_value_float(cam_handle, param, value)
    elif paramValueType == PropType.STRING:
        if not isinstance(value, str):
            raise TypeError()
        return kyfg_set_camera_value_string(cam_handle, param, value)
    elif paramValueType == PropType.COMMAND:
        if not isinstance(value, int):
            raise TypeError()
        param_str_buf = create_string_buffer(bytes(param.encode()))
        paramValue_p = c_int(value)
        kydll.KYFG_SetCameraValue.argtypes = (c_uint, c_char_p, c_void_p)
        kydll.KYFG_SetCameraValue.restype = c_uint32
        s = kydll.KYFG_SetCameraValue(cam_handle, param_str_buf, byref(paramValue_p))
    elif paramValueType == PropType.REGISTER:
        if not isinstance(value, (bytes, bytearray, list)):
            raise TypeError()
        return kyfg_set_camera_value_register(cam_handle, param, value)
    return None


def kyfg_set_camera_value_int(cam_handle, param, value):
    kydll.KYFG_SetCameraValueInt.argtypes = (c_uint, c_char_p, c_int64)
    kydll.KYFG_SetCameraValueInt.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))
    paramValue_p = c_int64(value)
    s = kydll.KYFG_SetCameraValueInt(cam_handle, param_str_buf, paramValue_p)


def kyfg_set_camera_value_float(cam_handle, param, value):
    kydll.KYFG_SetCameraValueFloat.argtypes = (c_uint, c_char_p, c_double)
    kydll.KYFG_SetCameraValueFloat.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))
    c_param_double_value = c_double(value)
    s = kydll.KYFG_SetCameraValueFloat(cam_handle, param_str_buf, c_param_double_value)


def kyfg_set_camera_value_bool(cam_handle, param, value):
    value_num = int(bool(value))
    value_c_style = c_ubyte(value_num)
    kydll.KYFG_SetCameraValueBool.argtypes = (c_uint, c_char_p, c_ubyte)
    kydll.KYFG_SetCameraValueBool.restype = c_uint
    param_str_buf = create_string_buffer(bytes(param.encode()))
    s = kydll.KYFG_SetCameraValueBool(cam_handle, param_str_buf, value_c_style)


def kyfg_set_camera_value_string(cam_handle, param, value):
    kydll.KYFG_SetCameraValueString.argtypes = (c_uint, c_char_p, c_char_p)
    kydll.KYFG_SetCameraValueString.restype = c_uint
    param_str_buf = create_string_buffer(bytes(param.encode()))
    value_str_buf = create_string_buffer(bytes(value.encode()))
    s = kydll.KYFG_SetCameraValueString(cam_handle, param_str_buf, value_str_buf)


def kyfg_set_camera_value_enum(cam_handle, param, value):
    value_c_style = c_int64(value)
    kydll.KYFG_SetCameraValueEnum.argtypes = (c_uint, c_char_p, c_int64)
    kydll.KYFG_SetCameraValueEnum.restype = c_uint
    param_str_buf = create_string_buffer(bytes(param.encode()))
    s = kydll.KYFG_SetCameraValueEnum(cam_handle, param_str_buf, value_c_style)


def kyfg_set_camera_value_enum_by_value_name(cam_handle, param, value_name):
    kydll.KYFG_SetCameraValueEnum_ByValueName.argtypes = (c_uint, c_char_p, c_char_p)
    kydll.KYFG_SetCameraValueEnum_ByValueName.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))
    paramValueName_str_buf = create_string_buffer(bytes(value_name.encode()))
    s = kydll.KYFG_SetCameraValueEnum_ByValueName(cam_handle, param_str_buf, paramValueName_str_buf)


def kyfg_set_camera_value_register(cam_handle, param, value):
    kydll.KYFG_SetCameraValue.argtypes = (c_uint, c_char_p, c_void_p)
    kydll.KYFG_SetCameraValue.restype = c_uint32
    param_str_buf = create_string_buffer(bytes(param.encode()))

    # Retrieving buffer size
    buffer_size = c_uint(0)
    kydll.KYFG_GetCameraValueRegister(cam_handle, param_str_buf, None, byref(buffer_size))

    carray = create_string_buffer(value, buffer_size.value)

    s = kydll.KYFG_SetCameraValue(cam_handle, param_str_buf, byref(carray))


def start_acquisition(cam_handle: int, stream_handle: int, frames: int):
    kydll.KYFG_CameraStart.argtypes = (c_uint, c_uint, c_uint)
    kydll.KYFG_CameraStart.restype = c_uint32
    s = kydll.KYFG_CameraStart(cam_handle, stream_handle, frames)


def stop_acquisition(cam_handle: int):
    kydll.KYFG_CameraStop.argtypes = (c_uint,)
    kydll.KYFG_CameraStop.restype = c_uint32
    s = kydll.KYFG_CameraStop(cam_handle)
