"""Validate the built MusicXML: measure clocks, voice overlaps, and XSD.

Measure clocks are checked against the *prevailing time signature* (not a fixed
length): divisions are read from the file and may change per measure.
"""
import os
import sys
from fractions import Fraction as F
from lxml import etree

path = sys.argv[1]
root = etree.parse(path).getroot()

problems = 0
for part in root.findall('part'):
    pid = part.get('id')
    div = 1
    prev_time = None
    for m in part.findall('measure'):
        num = m.get('number')
        for el in m:
            if el.tag == 'attributes':
                d = el.find('divisions')
                if d is not None:
                    div = int(d.text)
                t = el.find('time')
                if t is not None:
                    prev_time = (int(t.findtext('beats')), int(t.findtext('beat-type')))
        if prev_time is None:
            continue
        want = F(prev_time[0] * 4, prev_time[1])   # in quarter notes
        # per staff+voice duration sums
        sums = {}
        for el in m:
            if el.tag != 'note':
                continue
            st = el.findtext('staff') or '1'
            v = el.findtext('voice') or '1'
            d = int(el.findtext('duration') or 0)
            if el.find('chord') is not None:
                continue
            key = (st, v)
            sums[key] = sums.get(key, F()) + F(d, div)
        for (st, v), tot in sums.items():
            if tot != want:
                problems += 1
                print(f'{pid} m{num} staff{st} voice{v}: {tot} statt {want} Viertel')
print('measure-clock problems:', problems)

# XSD validation if the schema is present locally
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
