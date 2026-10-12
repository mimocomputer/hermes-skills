import pymupdf
d = pymupdf.open('source/01_Lobe_den_Herren.pdf')
for p in d:
    pix = p.get_pixmap(dpi=200)
    fn = f"work/page{p.number+1}_200.png"
    pix.save(fn)
    print(fn, pix.width, pix.height)
