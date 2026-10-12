"""Roundtrip check: built MusicXML vs MuseScore's export of the MSCZ.

Compares, per part/measure/staff/voice:
  - the note sequence (duration in divisions normalised to quarters, pitch)
  - the lyric syllables (text + syllabic) in musical order
Also verifies no lyric <text> contains a hyphen.
"""
import sys
from lxml import etree

DIV_A = None


def notes(path, part_ids=None):
    root = etree.parse(path).getroot()
    out = {}
    lyrics_by_part = {}
    bad_hyph = []
    for pi, part in enumerate(root.findall('part')):
        pid = part.get('id') or str(pi)
        seq = []
        ly = []
        for m in part.findall('measure'):
            num = int(m.get('number')) if m.get('number', '').isdigit() else 0
            cur = {}
            for el in m:
                if el.tag == 'backup':
                    cur = {}
                    continue
                if el.tag != 'note':
                    continue
                st = int(el.findtext('staff') or 1)
                v = el.findtext('voice') or '1'
                dur = int(el.findtext('duration') or 0)
                if el.find('chord') is not None:
                    # add pitch to previous note of same staff/voice
                    p = el.find('pitch')
                    if seq and p is not None:
                        seq[-1][4].append(p.findtext('step') + (p.findtext('alter') or '') + p.findtext('octave'))
                    continue
                p = el.find('pitch')
                pit = None if p is None else (p.findtext('step') + (p.findtext('alter') or '') + p.findtext('octave'))
                seq.append([num, st, v, dur, [pit] if pit else []])
                for l in el.findall('lyric'):
                    t = l.findtext('text') or ''
                    if '-' in t:
                        bad_hyph.append((pid, num, t))
                    ly.append((num, st, l.get('number'), t, l.findtext('syllabic') or ''))
            cur = {}
        out[pid] = seq
        lyrics_by_part[pid] = ly
    return out, lyrics_by_part, bad_hyph


a, la, ha = notes(sys.argv[1])
b, lb, hb = notes(sys.argv[2])
print('hyphen-in-text defects: built=%d exported=%d' % (len(ha), len(hb)))
if ha:
    print('  ', ha[:5])
if hb:
    print('  ', hb[:5])

# normalise durations: built uses /480 per quarter; exported divisions from the file
def norm(seq, path):
    root = etree.parse(path).getroot()
    div = int(root.findtext('part/measure/attributes/divisions') or 1)
    return [[n, s, v, round(d / div, 4), sorted(p)] for n, s, v, d, p in seq], div


A, divA = norm(a['P1'], sys.argv[1])
B, divB = norm(b[list(b)[0]], sys.argv[2])
print('divisions built=%s exported=%s' % (divA, divB))

# compare note multisets per (measure, staff)
from collections import Counter
cntA = Counter(tuple(x[:4]) for x in A)
cntB = Counter(tuple(x[:4]) for x in B)
print('part1 notes built=%d exported=%d' % (len(A), len(B)))
diff = (cntA - cntB) + (cntB - cntA)
print('note tuple differences:', sum(diff.values()))
for k, v in list(diff.items())[:10]:
    print('   ', k, v)

# compare pitch multisets per (measure, staff)
pa = Counter((x[0], x[1], tuple(x[4])) for x in A)
pb = Counter((x[0], x[1], tuple(x[4])) for x in B)
d2 = (pa - pb) + (pb - pa)
print('pitch differences:', sum(d2.values()))
for k, v in list(d2.items())[:10]:
    print('   ', k, v)

# lyric comparison
def lyc(part):
    return [(n, s, t, sy) for n, s, num, t, sy in part]


la1 = sorted(lyc(la['P1']))
lb1 = sorted(lyc(lb[list(lb)[0]]))
print('lyrics built=%d exported=%d' % (len(la1), len(lb1)))
ca, cb = Counter(la1), Counter(lb1)
d3 = (ca - cb) + (cb - ca)
print('lyric differences:', sum(d3.values()))
for k, v in list(d3.items())[:15]:
    print('   ', k, v)
