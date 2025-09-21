import contextlib
from ctypes import *
import dataclasses
import typing

from .base import *

__all__ = [
    'buffer_get_info',
    'open_stream',
    'stream_buffer_callback_register',
    'stream_buffer_callback_unregister',
    'stream_callback',

    'CallbackHandle',
    'StreamBufferInfoCmd',
]


def open_stream(cam_handle: int, frames: int):
    c_uint32_p = POINTER(c_uint)
    kydll.KYFG_StreamCreateAndAlloc.argtypes = (c_uint, c_uint32_p, c_uint, c_int)
    kydll.KYFG_StreamCreateAndAlloc.restype = c_uint32
    p_stream_handle_uin32 = c_uint(0)
    stream_c_uint_p = pointer(p_stream_handle_uin32)
    s = kydll.KYFG_StreamCreateAndAlloc(cam_handle, stream_c_uint_p, frames, 0)

    return p_stream_handle_uin32.value


@dataclasses.dataclass
class CallbackHandle:
    callback_wrapper: typing.Callable
    stream_handle: int
    removed: bool = False

    def remove(self):
        if self.removed:
            return
        stream_buffer_callback_unregister(self.stream_handle, self.callback_wrapper)


def stream_buffer_callback_register(stream_handle: int, callback, user_context):
    @CFUNCTYPE(None, c_uint64, c_void_p)
    def callback_wrapper(bh: int, user_ctx_ptr):
        user_ctx = cast(user_ctx_ptr, py_object).value
        callback(bh, user_ctx)

    kydll.KYFG_StreamBufferCallbackRegister.restype = c_uint32
    s = kydll.KYFG_StreamBufferCallbackRegister(stream_handle, callback_wrapper, py_object(user_context))

    return CallbackHandle(callback_wrapper, stream_handle)


def stream_buffer_callback_unregister(stream_handle: int, callback):
    kydll.KYFG_StreamBufferCallbackUnregister.restype = c_uint32

    s = kydll.KYFG_StreamBufferCallbackUnregister(stream_handle, callback)


@contextlib.contextmanager
def stream_callback(stream_handle: int, callback, user_context):
    ch = stream_buffer_callback_register(stream_handle, callback, user_context)
    try:
        yield
    finally:
        ch.remove()


# @formatter:off
class StreamBufferInfoCmd:
    BASE            = 0     # PTR           Base address of the buffer memory.
    SIZE            = 1     # SIZET         Size of the buffer in bytes. */
    PTR             = 2     # PTR           Private data pointer for the stream buffer. */
    TIMESTAMP       = 3     # UINT64        Timestamp the buffer was acquired. */
    INSTANTFPS      = 4     # FLOAT64       Instant FPS calculated from current and previous timestamp */
    IMAGEID         = 16    # UINT64        Image ID as reported by a transport protocol, e.g.CXP 's "source image index" */
    ID              = 1000  # UINT32        Unique id of buffer in the stream */
    STREAM_HANDLE   = 1001  # STREAM_HANDLE the handle of a stream to which this buffer belongs


class DataType:
    UNKNOWN     = 0     # Unknown data type
    STRING      = 1     # NULL-terminated C string (ASCII encoded).
    STRINGLIST  = 2     # Concatenated INFO_DATATYPE_STRING list. End of list is signaled with an additional NULL.
    INT16       = 3     # Signed 16 bit integer.
    UINT16      = 4     # Unsigned 16 bit integer
    INT32       = 5     # Signed 32 bit integer
    UINT32      = 6     # Unsigned 32 bit integer
    INT64       = 7     # Signed 64 bit integer
    UINT64      = 8     # Unsigned 64 bit integer
    FLOAT64     = 9     # Signed 64 bit floating point number.
    PTR         = 10    # Pointer type (void*). Size is platform dependent (32 bit on 32 bit platforms).
    BOOL8       = 11    # Boolean value occupying 8 bit. 0 for false and anything for true.
    SIZET       = 12    # Platform dependent unsigned integer (32 bit on 32 bit platforms).
    BUFFER      = 13    # Like a INFO_DATATYPE_STRING but with arbitrary data and no NULL termination.
    HANDLE      = 1001  # a STREAM_HANDLE.
    CAMHANDLE   = 1002  # a CAMHANDLE.
# @formatter:on


def buffer_get_info(stream_handle: int, stream_buffer_info_cmd: StreamBufferInfoCmd):
    c_uint64_p = POINTER(c_uint64)
    c_int_p = POINTER(c_int)
    kydll.KYFG_BufferGetInfo.argtypes = (c_uint64, c_int, c_void_p, c_uint64_p, c_int_p)
    kydll.KYFG_BufferGetInfo.restype = c_uint32

    info_size = c_uint64(0)
    info_type = c_int(0)
    # get type
    s = kydll.KYFG_BufferGetInfo(stream_handle, stream_buffer_info_cmd, None, byref(info_size), byref(info_type))

    if info_type.value == DataType.SIZET:
        info_value = c_size_t(0)
    elif info_type.value == DataType.UINT64:
        info_value = c_uint64(0)
    elif info_type.value == DataType.UINT32:
        info_value = c_uint32(0)
    elif info_type.value == DataType.UINT16:
        info_value = c_uint16(0)
    elif info_type.value == DataType.PTR:
        info_value = c_void_p(0)
    elif info_type.value == DataType.INT64:
        info_value = c_int64(0)
    elif info_type.value == DataType.INT32:
        info_value = c_int32(0)
    elif info_type.value == DataType.INT16:
        info_value = c_int16(0)
    elif info_type.value == DataType.FLOAT64:
        info_value = c_double(0)
    elif info_type.value == DataType.BOOL8:
        info_value = c_bool(False)
    elif info_type.value == DataType.HANDLE:
        info_value = c_uint32(0)
    elif info_type.value == DataType.CAMHANDLE:
        info_value = c_uint32(0)
    elif info_type.value == DataType.STRING:
        info_value = DevNameStr
    elif info_type.value == DataType.STRINGLIST:
        info_value = DevNameStr
    elif info_type.value == DataType.BUFFER:
        info_value = c_size_t * 256  # noqa
    else:
        return None

    # get value
    s = kydll.KYFG_BufferGetInfo(stream_handle, stream_buffer_info_cmd, byref(info_value), None, None)

    # https://stackoverflow.com/questions/46076118/python-how-interpret-memory-address-and-size-returned-by-dll-as-byte-array
    # pInfoBuffer_byte_array = string_at(info_value.value, info_size.value)

    return info_value.value
