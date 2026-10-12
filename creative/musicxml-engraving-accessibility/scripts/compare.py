"""Stack a source-scan crop above the render crop for visual comparison."""
import sys
import numpy as np
import pymupdf
from PIL import Image

src_page, x0, y0, x1, y1 = int(sys.argv[1]) - 1, *map(float, sys.argv[2:6])
ren_page, rx0, ry0, rx1, ry1 = int(sys.argv[6]) - 1, *map(float, sys.argv[7:11])
out = sys.argv[11]
dpi = int(sys.argv[12]) if len(sys.argv) > 12 else 300

src = pymupdf.open('source/01_Lobe_den_Herren.pdf')
ren = pymupdf.open('out/Lobe-den-Herren-DAISY.pdf')


def crop(doc, pno, x0, y0, x1, y1):
    p = doc[pno]
    r = p.rect
    clip = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height,
                        r.x0 + x1 * r.width, r.y0 + y1 * r.height)
    pix = p.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return Image.fromarray(arr).point(lambda v: 0 if v < 170 else 255)


A = crop(src, src_page, x0, y0, x1, y1)
B = crop(ren, ren_page, rx0, ry0, rx1, ry1)
w = max(A.width, B.width)
A = A.resize((int(A.width * w / A.width), int(A.height * w / A.width)))
B = B.resize((int(B.width * w / B.width), int(B.height * w / B.width)))
canvas = Image.new('L', (w, A.height + B.height + 30), 128)
canvas.paste(A, (0, 0))
canvas.paste(B, (0, A.height + 30))
canvas.save('work/' + out)
print('work/' + out, canvas.size)
