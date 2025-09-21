import contextlib
import ctypes
import enum
import functools
import threading
import typing

import cv2
import numpy as np

import kyapi

__all__ = [
    'Buffer',
    'Camera',
    'CameraStream',
    'FrameGrabber',
]


class GenICamPropMixIn:
    def __getattr__(self, item):
        return self.get_prop(item)

    def __setattr__(self, key, value):
        if key in self.__slots__:
            super().__setattr__(key, value)
        else:
            self.set_prop(key, value)

    def set(self, **kwargs):
        for k, v in kwargs.items():
            self.set_prop(k, v)


class HandleRegistryMixIn:
    _registry: dict[type, dict[int, ...]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls] = {}

    @classmethod
    def registry(cls):
        return cls._registry[cls]

    @classmethod
    def from_handle(cls, handle: int):
        return cls.registry()[handle]


class FrameGrabber(GenICamPropMixIn, HandleRegistryMixIn):
    __slots__ = ('index', 'handle')

    def __init__(self, index: int = 0):
        self.index = index
        self.handle = None

    def __repr__(self):
        return f'<FrameGrabber handle={self.handle}, index={self.index}>'

    def connect(self, scan_first: bool = True):
        if scan_first:
            kyapi.scan_frame_grabber()

        self.handle = kyapi.open_frame_grabber(self.index)
        self.registry()[self.handle] = self

    def disconnect(self):
        kyapi.close_frame_grabber(self.handle)
        del self.registry()[self.handle]
        self.handle = None

    @contextlib.contextmanager
    def open(self, scan_first: bool = True):
        self.connect(scan_first)
        try:
            yield self
        finally:
            self.disconnect()

    def get_camera(self, index: int = 0):
        cam_handles = kyapi.get_camera_handles(self.handle)
        if len(cam_handles) != 1:
            raise RuntimeError(f'Exactly one available camera expected, got {len(cam_handles)}')

        cam_handle = cam_handles[index]
        return Camera(self, index, cam_handle)

    @contextlib.contextmanager
    def open_camera(self, index: int = 0):
        with self.get_camera(index).open() as cam:
            yield cam

    def get_info(self):
        return kyapi.get_frame_grabber_info(self.index)

    def get_prop(self, name: str):
        return kyapi.get_grabber_value(self.handle, name)

    def set_prop(self, name: str, value):
        if isinstance(value, enum.Enum):
            value = value.value
        return kyapi.set_grabber_value(self.handle, name, value)

    @property
    def connected(self):
        return self.handle is not None


class Camera(GenICamPropMixIn, HandleRegistryMixIn):
    __slots__ = ('fg', 'index', 'handle', 'stream', 'end_event', 'working')

    def __init__(self, fg: FrameGrabber, index: int = 0, handle: int = None):
        self.fg = fg
        self.index = index
        self.handle = handle
        self.stream = None
        self.end_event = None
        self.working = False

    def __repr__(self):
        return f'<Camera handle={self.handle}, fg={self.fg.handle}, index={self.index}>'

    def connect(self):
        kyapi.open_camera(self.handle)
        self.registry()[self.handle] = self

    def disconnect(self):
        kyapi.close_camera(self.handle)
        del self.registry()[self.handle]

    @contextlib.contextmanager
    def open(self):
        self.connect()
        try:
            yield self
        finally:
            self.disconnect()

    @contextlib.contextmanager
    def open_stream(self, frames: int):
        if self.stream is not None:
            raise RuntimeError(f'At most one stream can be opened at a time')

        with CameraStream(self, frames).open() as stream:
            self.stream = stream
            try:
                yield stream
            finally:
                self.stream = None

    def get_info(self):
        return kyapi.get_cam_info(self.handle)

    def get_prop(self, name: str):
        return kyapi.get_camera_prop(self.handle, name)

    def set_prop(self, name: str, value):
        if isinstance(value, enum.Enum):
            value = value.value
        return kyapi.set_camera_prop(self.handle, name, value)

    def start(self, n_frame: int = 0, use_default_callback: bool = True, block: bool = True):
        if self.working:
            raise RuntimeError(f'The camera is already working')
        if self.stream is None:
            raise RuntimeError(f'No stream opened')

        if len(self.stream.callback_handles) == 0 and use_default_callback:
            self.stream.register_callback(multi_frame_default_callback)

        self.working = True
        if block:
            self.end_event = threading.Event()
        kyapi.start_acquisition(self.handle, self.stream.handle, n_frame)

    def stop(self):
        if not self.working:
            raise RuntimeError(f'The camera is not working')

        kyapi.stop_acquisition(self.handle)
        self.end_event = None
        self.working = False

    def await_acquisition(self, timeout: float = None):
        if self.end_event is None:
            return
        self.end_event.wait(timeout)

    def finish_acquisition(self):
        if self.end_event is None:
            return
        self.end_event.set()

    def capture(self, n_frame: int = 0, timeout: float = None, block: bool = True):
        try:
            self.start(n_frame, block=block)
            # If block, wait until finish_acquisition is called or timeout
            # If not block, do nothing and return immediately
            self.await_acquisition(timeout)
        except KeyboardInterrupt:
            print('Acquisition interrupted')
        finally:
            self.stop()

        return self.stream.frames

    def roi(self, offset_x: int = None, offset_y: int = None, width: int = None, height: int = None):
        if self.working:
            raise RuntimeError(f'{self.roi.__qualname__} cannot be called while the camera is working')
        if offset_x is None and offset_y is None and width is None and height is None:
            return self.OffsetX, self.OffsetY, self.Width, self.Height

        if offset_x is not None:
            self.set_prop('OffsetX', offset_x)
        if offset_y is not None:
            self.set_prop('OffsetY', offset_y)
        if width is not None:
            self.set_prop('Width', width)
        if height is not None:
            self.set_prop('Height', height)

    def center_roi(self, width: int, height: int):
        offset_x = (self.WidthMax - width) // 2
        offset_y = (self.HeightMax - height) // 2
        self.roi(offset_x, offset_y, width, height)

    @property
    def connected(self):
        return self.handle in self.registry()


class CameraStream(HandleRegistryMixIn):
    def __init__(self, cam: Camera, n_frame: int):
        self.cam = cam
        self.n_frame = n_frame
        self.handle = None
        self.callback_handles = []
        self.frames = []

    def __repr__(self):
        return f'<CameraStream handle={self.handle}, cam={self.cam.handle}, n_frame={self.n_frame}>'

    def allocate(self):
        self.handle = kyapi.open_stream(self.cam.handle, self.n_frame)
        self.registry()[self.handle] = self

    def free(self):
        self.clear_callback()
        del self.registry()[self.handle]
        self.handle = None

    def register_native_callback(self, callback, user_context):
        callback_handle = kyapi.stream_buffer_callback_register(self.handle, callback, user_context)
        self.callback_handles.append(callback_handle)
        return callback_handle

    def register_callback(self, callback, *args, **kwargs):
        def native_callback(buffer_handle, _):
            buffer = Buffer(self, buffer_handle)
            callback(buffer, *args, **kwargs)

        self.register_native_callback(native_callback, None)

    def clear_callback(self):
        for callback_handle in self.callback_handles:
            callback_handle.remove()
        self.callback_handles.clear()

    @contextlib.contextmanager
    def open(self):
        self.allocate()
        try:
            yield self
        finally:
            self.free()

    @property
    def allocated(self):
        return self.handle is not None


class Buffer:
    def __init__(self, stream: CameraStream, handle: int):
        self.stream = stream
        self.handle = handle

    def __repr__(self):
        return f'<{self.__class__.__name__} handle={self.handle}, stream={self.stream.handle}>'

    def __str__(self):
        s = ', '.join(f'{k}={getattr(self, k)}' for k in [
            'base', 'size', 'ptr', 'timestamp', 'instant_fps', 'image_id', 'id',
        ])
        return f'{self.__class__.__name__}({s})'

    def get_image(self, demosaic: typing.Literal['interpolate', 'downsample', 'none'] = 'interpolate'):
        cam = self.stream.cam
        image_data = np.zeros(self.size, dtype=np.uint8)

        ctypes.memmove(image_data.ctypes.data, self.base, self.size)

        w, h = cam.Width, cam.Height  # TODO: optimize
        image = image_data.reshape((h, w, 1))

        if demosaic == 'interpolate':
            image = cv2.cvtColor(image, cv2.COLOR_BAYER_RGGB2RGB)
        elif demosaic == 'downsample':
            image = image.astype(np.float32)
            image = raw2rgb_downsample(image)
            image = image.astype(np.uint8)
        elif demosaic == 'none':
            pass

        return image

    @property
    @functools.cache
    def base(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.BASE)

    @property
    @functools.cache
    def size(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.SIZE)

    @property
    @functools.cache
    def ptr(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.PTR)

    @property
    @functools.cache
    def timestamp(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.TIMESTAMP)

    @property
    @functools.cache
    def instant_fps(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.INSTANTFPS)

    @property
    @functools.cache
    def image_id(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.IMAGEID)

    @property
    @functools.cache
    def id(self):
        return kyapi.buffer_get_info(self.handle, kyapi.StreamBufferInfoCmd.ID)


def raw2rgb_downsample(image: np.ndarray) -> np.ndarray:
    r = image[0::2, 0::2]
    g = (image[0::2, 1::2] + image[1::2, 0::2]) / 2
    b = image[1::2, 1::2]
    return np.concat([r, g, b], axis=-1)


def multi_frame_default_callback(buffer: Buffer):
    stream = buffer.stream

    if not stream.cam.working:
        return
    if buffer.base is None:
        stream.cam.finish_acquisition()
        return

    image = buffer.get_image()
    stream.frames.append(image)
