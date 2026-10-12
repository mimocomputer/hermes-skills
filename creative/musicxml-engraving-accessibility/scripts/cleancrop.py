"""Clean crop: threshold out the grey watermark, upscale, save PNG for reading."""
import sys
import numpy as np
import pymupdf
from PIL import Image

page = int(sys.argv[1]) - 1
x0, y0, x1, y1 = map(float, sys.argv[2:6])
out = sys.argv[6]
dpi = int(sys.argv[7]) if len(sys.argv) > 7 else 400
thr = int(sys.argv[8]) if len(sys.argv) > 8 else 160

doc = pymupdf.open('source/01_Lobe_den_Herren.pdf')
p = doc[page]
r = p.rect
clip = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height,
                    r.x0 + x1 * r.width, r.y0 + y1 * r.height)
pix = p.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
print('grey percentiles', np.percentile(arr, [1, 5, 20, 50, 80, 95]))
clean = np.where(arr < thr, 0, 255).astype(np.uint8)
Image.fromarray(clean).save('work/' + out)
print('work/' + out, clean.shape)
