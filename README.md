# pykyfg

A high-level Python API for KAYA frame grabber hardware, providing easy-to-use interfaces for camera control, image acquisition, and streaming.

## ⚠️ Important Notice

**This package provides only basic functionality and does not fully support all KAYA API features.**

For complete KAYA API support and official documentation, please refer to the official [KAYA Vision Point SDK](https://kayainstruments.com/software-sdk/)

**Disclaimer**: This package is developed by a third party and is not affiliated with or endorsed by KAYA Instruments. KAYA Instruments assumes no responsibility for this package or its use.

## Overview

pykyfg is a Python wrapper around the KAYA frame grabber SDK, designed to simplify camera operations and image acquisition workflows. It provides both low-level bindings (`kyapi`) and high-level abstractions (`pykyfg`) for working with KAYA hardware.

## Installation

Install directly using pip:

```bash
pip install pykyfg
```

### Prerequisites

- Python 3.8+
- KAYA frame grabber and camera hardware
- KAYA Vision Point SDK installed and configured

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
