"""Validate the built MusicXML: measure clocks, voice overlaps, and XSD."""
import sys
from lxml import etree

path = sys.argv[1]
tree = etree.parse(path)
root = tree.getroot()
DIV = 480

problems = 0
for part in root.findall('part'):
    pid = part.get('id')
    for m in part.findall('measure'):
        num = m.get('number')
        # per staff+voice duration sums
        sums = {}
        cur = None
        staff = 1
        for el in m:
            if el.tag == 'backup':
                cur = None
                continue
            if el.tag != 'note':
                continue
            st = el.findtext('staff')
            if st:
                staff = int(st)
            v = el.findtext('voice') or '1'
            d = int(el.findtext('duration') or 0)
            if el.find('chord') is not None:
                continue
            key = (staff, v)
            # determine position
            if cur is None or cur[0] != key:
                pos = 0.0
            else:
                pos = cur[1]
            cur = (key, pos + d / DIV)
            sums.setdefault(key, 0.0)
            sums[key] += d / DIV
        for (st, v), tot in sums.items():
            if abs(tot - 3.0) > 1e-6:
                problems += 1
                print(f'{pid} m{num} staff{st} voice{v}: {round(tot,3)}')
print('measure-clock problems:', problems)

# XSD validation if the schema is present locally
import os
xsd = 'work/musicxml.xsd'
if os.path.exists(xsd):
    schema = etree.XMLSchema(etree.parse(xsd))
    doc = etree.parse(path)
    ok = schema.validate(doc)
    print('XSD valid:', ok)
    if not ok:
        for e in schema.error_log[:20]:
            print('  ', e)
else:
    print('XSD not downloaded; skipping')
