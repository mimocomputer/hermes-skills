"""Compare pitched notes only (built vs MuseScore export), and check the MIDI."""
import sys
from collections import Counter
from lxml import etree


def pitched(path):
    root = etree.parse(path).getroot()
    div = int(root.findtext('part/measure/attributes/divisions') or 1)
    res = {}
    for pi, part in enumerate(root.findall('part')):
        seq = []
        for m in part.findall('measure'):
            num = int(m.get('number')) if m.get('number', '').isdigit() else 0
            for el in m:
                if el.tag != 'note' or el.find('pitch') is None:
                    continue
                st = int(el.findtext('staff') or 1)
                v = el.findtext('voice') or '1'
                dur = round(int(el.findtext('duration') or 0) / div, 4)
                p = el.find('pitch')
                pit = p.findtext('step') + (p.findtext('alter') or '') + p.findtext('octave')
                seq.append((num, st, v, dur, pit))
        res['P%d' % (pi + 1)] = seq
    return res


A = pitched(sys.argv[1])
B = pitched(sys.argv[2])
for k in A:
    ca = Counter(A[k])
    cb = Counter(B.get(k, []))
    d = (ca - cb) + (cb - ca)
    print(f'{k}: built={len(A[k])} exported={len(B.get(k, []))} diffs={sum(d.values())}')
    for kk, vv in list(d.items())[:12]:
        print('    ', kk, vv)
print('total built pitches:', sum(len(v) for v in A.values()),
      'exported:', sum(len(v) for v in B.values()))
