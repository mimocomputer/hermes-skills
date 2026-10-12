"""Notehead detector for a given staff band.

usage: heads4.py <page> <topline_y> <botline_y> <clef G|F> <x0> <x1> [dpi]
All coordinates in dpi pixels (default 150 = native raster).
Prints notehead centres mapped to pitch names, grouped into chords by x.
"""
import sys
import numpy as np
import pymupdf
from scipy import ndimage

page_no = int(sys.argv[1]) - 1
top, bot = float(sys.argv[2]), float(sys.argv[3])
clef = sys.argv[4]
x0, x1 = float(sys.argv[5]), float(sys.argv[6])
dpi = int(sys.argv[7]) if len(sys.argv) > 7 else 150

doc = pymupdf.open('source/01_Lobe_den_Herren.pdf')
pix = doc[page_no].get_pixmap(dpi=dpi)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n > 1:
    img = img[:, :, 0]
scale = dpi / 150.0
top, bot = top * scale, bot * scale
x0, x1 = x0 * scale, x1 * scale
ink = (img < 140)

# drop staff lines
mask = ink.copy()
for r in range(int(top) - 3, int(bot) + 4):
    row = mask[r, int(x0):int(x1)]
    if row.mean() > 0.6:
        mask[r, :] = False

er = ndimage.binary_erosion(mask, structure=np.ones((1, 5)))
lab, n = ndimage.label(er, structure=np.ones((3, 3)))
objs = ndimage.find_objects(lab)
step_px = (bot - top) / 8.0
names = ['C', 'D', 'E', 'F', 'G', 'A', 'B']


def pitch_name(steps):
    topname = 'F5' if clef == 'G' else 'A3'
    idx = names.index(topname[0]) - steps
    return names[idx % 7] + str(int(topname[1]) + idx // 7)


heads = []
for i, sl in enumerate(objs, start=1):
    ys, xs = sl
    h, w = ys.stop - ys.start, xs.stop - xs.start
    if not (5 <= w <= 16 and 4 <= h <= 11):
        continue
    cy = (ys.start + ys.stop) / 2.0
    cx = (xs.start + xs.stop) / 2.0
    if not (top - 45 <= cy <= bot + 45 and x0 <= cx <= x1):
        continue
    steps = int(round((cy - top) / step_px))
    heads.append((cx, cy, w, h, pitch_name(steps)))

heads.sort()
chords = []
for cx, cy, w, h, p in heads:
    if chords and abs(cx - chords[-1][-1][0]) <= 6:
        chords[-1].append((cx, cy, w, h, p))
    else:
        chords.append([(cx, cy, w, h, p)])
for ch in chords:
    xs = [round(c[0]) for c in ch]
    ps = sorted({c[4] for c in ch})
    print(f"x={xs[0]:>4}..{xs[-1]:>4}  " + ' '.join(ps) + '   raw=' + str([(round(c[0]), round(c[1]), c[4]) for c in ch]))
