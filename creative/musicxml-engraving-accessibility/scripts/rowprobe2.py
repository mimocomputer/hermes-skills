import numpy as np, pymupdf
doc = pymupdf.open('source/01_Lobe_den_Herren.pdf')
for pno in (0, 1, 2):
    pix = doc[pno].get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, 0]
    print('=== page', pno + 1)
    for thr, frac in ((200, 0.2), (215, 0.15)):
        ink = img < thr
        rc = ink.sum(axis=1)
        rows = [r for r in range(pix.height) if rc[r] > frac * pix.width]
        grp = []
        for r in rows:
            if grp and r - grp[-1][-1] <= 3:
                grp[-1].append(r)
            else:
                grp.append([r])
        print('  thr', thr, [int(np.mean(g)) for g in grp])
