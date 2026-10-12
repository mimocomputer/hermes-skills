"""Verify every measure/voice of the OMR mscx sums to the 3/4 bar length.

Applies tuplet ratios, which the plain parser ignored.
"""
import sys
import xml.etree.ElementTree as ET

DIV = 480.0
DUR = {'whole': 4.0, 'half': 2.0, 'quarter': 1.0, 'eighth': 0.5, '16th': 0.25,
       '32nd': 0.125, '64th': 0.0625, '128th': 0.03125, '256th': 0.015625,
       'breve': 8.0, 'longa': 16.0, '512th': 0.0078125}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def pname(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


path = sys.argv[1] if len(sys.argv) > 1 else 'work/omr.mscx'
root = ET.parse(path).getroot()
blocks = [s for s in root.iter('Staff') if s.find('Measure') is not None]

bad = 0
for s in blocks:
    sid = s.get('id')
    base = (int(sid) - 1) * 4
    for m in s.findall('Measure'):
        num = m.get('number')
        # tuplet definitions in this measure: id -> (normal, actual)
        tups = {}
        for t in m.findall('Tuplet'):
            tups[t.get('id')] = (int(t.findtext('normalNotes') or 2),
                                 int(t.findtext('actualNotes') or 3))
        voices = {}
        for el in m:
            if el.tag not in ('Chord', 'Rest'):
                continue
            tr = el.findtext('track')
            voice = (int(tr) - base) if tr is not None else 0
            dt = el.findtext('durationType')
            if dt == 'measure':
                d = 3.0
            else:
                b = DUR.get(dt)
                if b is None:
                    print('  unknown durationType', dt)
                    b = 1.0
                dots = int(el.findtext('dots') or 0)
                d = b
                add = b / 2
                for _ in range(dots):
                    d += add
                    add /= 2
            tref = el.findtext('Tuplet')
            if tref and tref in tups:
                n, a = tups[tref]
                d = d * n / a
            voices.setdefault(voice, []).append((d, el))
        for v, items in voices.items():
            tot = sum(x[0] for x in items)
            if abs(tot - 3.0) > 1e-6:
                bad += 1
                seq = ' '.join(
                    (('R' if el.tag == 'Rest' else '+'.join(pname(int(n.findtext('pitch')))
                      for n in el.findall('Note'))) + f"({round(d,3)})")
                    for d, el in items)
                print(f'STAFF {sid} m{num} v{v}: sum={round(tot,3)}  {seq}')
print('invalid voice-measures:', bad)
