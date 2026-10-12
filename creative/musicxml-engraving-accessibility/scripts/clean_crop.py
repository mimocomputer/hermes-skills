#!/usr/bin/env python3
"""Thresholded crop of a scanned score page, sized for visual reading.

usage: clean_crop.py <pdf> <page 1-based> <x0> <y0> <x1> <y1> <out.png> [dpi] [grey_threshold]

Coordinates are fractions of the page. Ink darker than the grey threshold is kept
black, everything else becomes white, which removes watermarks and show-through.
Warns when the crop exceeds ~1.1 MPix, i.e. when a reading model will downscale it.
"""
import sys

import numpy as np
import pymupdf
from PIL import Image

pdf, page, x0, y0, x1, y1, out = sys.argv[1:8]
dpi = int(sys.argv[8]) if len(sys.argv) > 8 else 500
thr = int(sys.argv[9]) if len(sys.argv) > 9 else 160

doc = pymupdf.open(pdf)
p = doc[int(page) - 1]
r = p.rect
clip = pymupdf.Rect(r.x0 + float(x0) * r.width, r.y0 + float(y0) * r.height,
                    r.x0 + float(x1) * r.width, r.y0 + float(y1) * r.height)
pix = p.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
if arr.shape[0] * arr.shape[1] > 1_100_000:
    print('warning: crop over ~1.1 MPix - it will be downscaled for reading')
Image.fromarray(np.where(arr < thr, 0, 255).astype(np.uint8)).save(out)
print(out, arr.shape)
