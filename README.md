# pykyfg

A high-level Python API for KAYA frame grabber hardware, providing easy-to-use interfaces for camera control, image acquisition, and streaming.

## Overview

pykyfg is a Python wrapper around the KAYA frame grabber SDK, designed to simplify camera operations and image acquisition workflows. It provides both low-level bindings (`kyapi`) and high-level abstractions (`pykyfg`) for working with KAYA hardware.

## Features

- **Camera Management**: Easy camera discovery, connection, and configuration
- **Frame Acquisition**: High-performance image capture with buffer management
- **Streaming Support**: Real-time video streaming with callback support
- **GenICam Integration**: Access to standard camera features through GenICam interface
- **OpenCV Integration**: Seamless integration with OpenCV for image processing

## Installation

### Prerequisites

- Python 3.7+
- KAYA frame grabber and camera hardware
- KAYA Vision Point I API

### Install from Source

```bash
git clone <repository-url>
cd KAYA-FG
pip install -e .
```

### Dependencies

- `numpy` - Numerical computing
- `opencv-python` - Computer vision library

## Quick Start

```python
import pykyfg
import cv2

with pykyfg.FrameGrabber().open() as fg:
    with fg.open_camera() as cam:
        with cam.open_stream(4) as stream:
            frames = cam.capture(1)

            
for frame in frames:
    cv2.imshow("Frame", frame)
    cv2.waitKey(0)
cv2.destroyAllWindows()
```

## Hardware Requirements

- KAYA frame grabber card
- Compatible camera (GigE Vision, USB3 Vision, or Camera Link)
- Windows/Linux system with KAYA drivers installed
