"""Detect barlines as columns whose ink is continuous across both organ staves.

usage: barlines2.py <page> <top_line_upper_staff> <bottom_line_lower_staff>
"""
import sys
import numpy as np
import pymupdf

page_no = int(sys.argv[1]) - 1
top = int(float(sys.argv[2]))
bot = int(float(sys.argv[3]))
doc = pymupdf.open('source/01_Lobe_den_Herren.pdf')
pix = doc[page_no].get_pixmap(dpi=150)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, 0]
ink = img < 150
res = []
for x in range(pix.width):
    col = ink[top:bot + 1, x]
    # longest white gap
    gap = best = 0
    for v in col:
        if v:
            gap = 0
        else:
            gap += 1
            best = max(best, gap)
    if best <= 6:
        res.append(x)
groups = []
for x in res:
    if groups and x - groups[-1][-1] <= 2:
        groups[-1].append(x)
    else:
        groups.append([x])
print('barline columns:', [int(np.mean(g)) for g in groups])
