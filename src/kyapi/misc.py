import dataclasses
from ctypes import *

from .base import kydll

__all__ = [
    'get_software_version',
    'init',
]


class CInitParam(Structure):
    _pack_ = 1
    _fields_ = [
        ("version", c_uint),
        # since version 1
        ("concurrency_mode", c_uint),
        ("logging_mode", c_uint),
        # since version 2
        ("noVideoStreamProcess", c_bool)
    ]


@dataclasses.dataclass
class SoftwareVersion:
    struct_version: int = 1  # Must be set to 0 or 1 before calling KY_GetSoftwareVersion() function
    major: int = 0
    minor: int = 0
    patch: int = 0
    # since version 1
    beta: int = 0  # Non-zero value indicates a "Beta build"
    rc: int = 0  # Non-zero value indicates a "Release Candidate build"
    # since version 2
    alpha: int = 0  # Non-zero value indicates a "Alpha build"


class CSoftwareVersion(Structure):
    _fields_ = [
        ("struct_version", c_uint16),
        ("Major", c_uint16),
        ("Minor", c_uint16),
        ("SubMinor", c_uint16),
        # since version 1
        ("Beta", c_uint16),  # Non-zero value indicates a "Beta build"
        ("RC", c_uint16),  # Non-zero value indicates a "Release Candidate build"
        # since version 2
        ("Alpha", c_uint16)  # Non-zero value indicates a "Alpha build"
    ]


def get_software_version():
    c_sv_pointer = POINTER(CSoftwareVersion)
    kydll.KY_GetSoftwareVersion.argtypes = (c_sv_pointer,)
    kydll.KY_GetSoftwareVersion.restype = c_uint32

    v = CSoftwareVersion()
    v.struct_version = 2
    s = kydll.KY_GetSoftwareVersion(byref(v))

    sv = SoftwareVersion(v.struct_version, v.Major, v.Minor, v.SubMinor, v.Beta, v.RC, v.Alpha)
    return sv


def init(version: int = 2, concurrency_mode: int = 0, logging_mode: int = 0, no_video_stream_process: bool = False):
    c_init_param_ptr = POINTER(CInitParam)
    kydll.KYFGLib_Initialize.argtypes = (c_init_param_ptr,)
    kydll.KYFGLib_Initialize.restype = c_uint32

    init_params = CInitParam(version, concurrency_mode, logging_mode, no_video_stream_process)

    s = kydll.KYFGLib_Initialize(byref(init_params))
