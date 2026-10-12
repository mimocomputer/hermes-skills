from lxml import etree
import sys

t = etree.parse(sys.argv[1])
root = t.getroot()
part = root.find('part')
lo, hi = int(sys.argv[2]), int(sys.argv[3])
for m in part.findall('measure'):
    num = int(m.get('number'))
    if not (lo <= num <= hi):
        continue
    row = {}
    for el in m.findall('note'):
        st = el.findtext('staff')
        for l in el.findall('lyric'):
            row.setdefault((st, l.get('number')), []).append(
                f"{l.findtext('text')}[{(l.findtext('syllabic') or '[')[0]}]")
    for (st, n), items in sorted(row.items()):
        print(f'm{num} staff{st} verse{n}: ' + ' '.join(items))
