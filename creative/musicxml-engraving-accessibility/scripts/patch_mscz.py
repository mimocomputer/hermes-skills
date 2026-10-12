"""Patch a MuseScore 4 .mscz: enable hide-empty-staves and set page format."""
import sys
import re
import shutil
import zipfile
import os

path = sys.argv[1]
tmp = path + '.work'
shutil.copy(path, tmp)
with zipfile.ZipFile(tmp) as z:
    names = z.namelist()
    data = {n: z.read(n) for n in names}

style = data.get('score_style.mss')
if style is None:
    styles = [n for n in names if n.endswith('.mss')]
    style_name = styles[0]
else:
    style_name = 'score_style.mss'
txt = data[style_name].decode('utf-8')
txt = re.sub(r'<hideEmptyStaves>\d</hideEmptyStaves>',
             '<hideEmptyStaves>1</hideEmptyStaves>', txt)
txt = re.sub(r'<dontHideStavesInFirstSystem>\d</dontHideStavesInFirstSystem>',
             '<dontHideStavesInFirstSystem>0</dontHideStavesInFirstSystem>', txt)
# tighter horizontal spacing so that the printed measure counts per system fit
txt = re.sub(r'<measureSpacing>[^<]*</measureSpacing>',
             '<measureSpacing>1</measureSpacing>', txt)
data[style_name] = txt.encode('utf-8')

with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for n in names:
        z.writestr(n, data[n])
os.remove(tmp)
print('patched', path, '(hideEmptyStaves=1)')
