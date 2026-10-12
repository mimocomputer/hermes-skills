"""Build corrected MusicXML editions (master + DAISY) from the OMR mscx.

usage: build_musicxml.py <master|daisy> <outfile>
"""
import sys
from lxml import etree

sys.path.insert(0, 'scripts')
from mscx_read import read

DIV = 480
BAR = 3.0

LYRIC_FIX = {
    ('mich', 14): 'mäch',
    ('Ko', 15): 'Kö',
    ('Cho', 22): 'Chö',
    ('Leb', 30): 'Lob',
    ('hor', 31): 'hö',
    ('fuh', 43): 'füh',
    ('mich', 48): 'mäch',
    ('mir', 60): 'mit',
    ('heil', 63): 'heiß',
    ('halt', 46): 'hält',
    ('halt,', 46): 'hält,',
    ('gill', 69): 'giß',
    ('Cho', 22): 'Chö',
    ('Stro', 41): 'Strö',
    ('drin', 35): 'dein',
    ('kran.', 49): 'kann,',
}

VERSE_DIGIT = {12: '1.', 33: '2.', 54: '4.'}

LABELS = [
    (1, 'P2', 1, 'Tpts.'),
    (1, 'P2', 1, 'Maestoso con moto'),
    (3, 'P2', 1, 'Org.'),
    (12, 'P1', 1, 'CHOR und GEMEINDE'),
    (12, 'P2', 1, '(Org. und Orch.)'),
    (33, 'P1', 1, 'v. 2: CHOR und ORGEL'),
    (33, 'P1', 2, 'v. 3: CHOR allein'),
    (54, 'P1', 1, 'SOPRANEN'),
    (54, 'P1', 2, 'ALLE ANDERE STIMMEN'),
    (54, 'P2', 1, '(Org. und Orch.)'),
    (65, 'P1', 1, 'cresc.'),
]

DYNAMICS = [
    (1, 'P2', 1, 'f'),
    (3, 'P2', 1, 'ff'),
    (12, 'P1', 1, 'f'),
    (33, 'P1', 1, 'mf'),
    (54, 'P1', 1, 'f'),
]

PART_NAME = {'P1': ('Chor', 'Chor'), 'P2': ('Orgel', 'Org.')}
LYOUT = [('P1', 1, 1), ('P1', 2, 4), ('P2', 1, 2), ('P2', 2, 3)]
# system / page breaks as printed in the source
NEW_SYSTEM = {6, 12, 19, 26, 33, 40, 47, 54, 61, 68}
NEW_PAGE = {26, 54}
TYPEMAP = {4.0: 'whole', 2.0: 'half', 1.0: 'quarter', 0.5: 'eighth',
           0.25: '16th', 0.125: '32nd', 0.0625: '64th'}


def verse_for(measure, src_row):
    m = int(measure)
    if 12 <= m <= 32:
        return 1
    if 33 <= m <= 53:
        return 2 if src_row == 0 else 3
    if 54 <= m <= 74:
        return 4
    return None


SEMI = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
# MuseScore tpc -> (step, alter); step order is the circle of fifths
TPC_NATURAL = {'C': 14, 'D': 16, 'E': 18, 'F': 13, 'G': 15, 'A': 17, 'B': 19}
STEPS = ['F', 'C', 'G', 'D', 'A', 'E', 'B']


def tpc_to_step_alter(tpc):
    for step in ('C', 'D', 'E', 'F', 'G', 'A', 'B'):
        nat = TPC_NATURAL[step]
        if (tpc - nat) % 7 == 0:
            return step, (tpc - nat) // 7
    return None, 0


def pitch_el(midi, tpc=None):
    """Emit a <pitch> honouring MuseScore's tpc spelling when available."""
    if tpc is not None and tpc != -99:
        step, alter = tpc_to_step_alter(tpc)
        if step:
            octave = (midi - alter - SEMI[step]) // 12 - 1
            p = etree.Element('pitch')
            etree.SubElement(p, 'step').text = step
            if alter:
                etree.SubElement(p, 'alter').text = str(alter)
            etree.SubElement(p, 'octave').text = str(octave)
            return p
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    n = names[midi % 12]
    p = etree.Element('pitch')
    etree.SubElement(p, 'step').text = n[0]
    if n.endswith('#'):
        etree.SubElement(p, 'alter').text = '1'
    etree.SubElement(p, 'octave').text = str(midi // 12 - 1)
    return p


def build(daisy):
    staves = read('work/omr.mscx')
    nmeas = 74

    # syllabic reconstruction: walk each (staff, measure, lyric-index) sequence
    syll_flags = {}
    for sid, ml in staves.items():
        byrow = {}
        for mi, m in enumerate(ml[:nmeas]):
            for ev in m['events']:
                for li, ly in enumerate(ev['lyrics']):
                    if verse_for(m['number'], ly['no']) is None:
                        continue
                    byrow.setdefault(ly['no'], []).append(
                        (mi, round(ev['onset'], 4), li, ly['text'], ly['syllabic']))
        for row, seq in byrow.items():
            prev = None
            for mi, onset, li, text, given in seq:
                if given in ('begin', 'middle', 'end', 'single'):
                    flag = given
                elif given in ('', None):
                    flag = 'end' if prev in ('begin', 'middle') else 'single'
                else:
                    flag = 'single'
                prev = flag
                syll_flags[(sid, mi, row, onset, li)] = flag

    root = etree.Element('score-partwise', version='4.0')
    defaults = etree.Element('defaults')
    scaling = etree.SubElement(defaults, 'scaling')
    # the printed source has a staff space of 1.27 mm; tenths are 1/10 spatium
    etree.SubElement(scaling, 'millimeters').text = '5.08'
    etree.SubElement(scaling, 'tenths').text = '40'
    if daisy:
        wk = etree.SubElement(root, 'work')
        etree.SubElement(wk, 'work-title').text = 'Lobe den Herren'
    etree.SubElement(root, 'movement-title').text = 'Lobe den Herren'
    ident = etree.SubElement(root, 'identification')
    etree.SubElement(ident, 'creator', type='composer').text = 'Stralsund Gesangbuch 1665'
    etree.SubElement(ident, 'creator', type='arranger').text = 'John Rutter'
    enc = etree.SubElement(ident, 'encoding')
    etree.SubElement(enc, 'software').text = 'Hermes correction pipeline (MuseScore 4.7.5)'
    etree.SubElement(enc, 'encoding-description').text = (
        'Notes corrected against the printed source; accessibility edition prepared '
        'according to the DAISY music braille engraving guidelines' if daisy else
        'Corrected against the printed source')
    etree.SubElement(ident, 'source').text = '01_Lobe_den_Herren.pdf'
    root.append(defaults)
    pl = etree.SubElement(root, 'part-list')
    for pid in ('P1', 'P2'):
        sp = etree.SubElement(pl, 'score-part', id=pid)
        etree.SubElement(sp, 'part-name').text = PART_NAME[pid][0]
        etree.SubElement(sp, 'part-abbreviation').text = PART_NAME[pid][1]
        si = etree.SubElement(sp, 'score-instrument', id=pid + '-I1')
        etree.SubElement(si, 'instrument-name').text = PART_NAME[pid][0]

    for pid in ('P1', 'P2'):
        part = etree.SubElement(root, 'part', id=pid)
        stave_map = [(ost, ssrc) for p, ost, ssrc in LYOUT if p == pid]
        for mi in range(nmeas):
            num = mi + 1
            meas = etree.SubElement(part, 'measure', number=str(num))
            if num in NEW_SYSTEM:
                if num in NEW_PAGE:
                    etree.SubElement(meas, 'print', **{'new-page': 'yes'})
                else:
                    etree.SubElement(meas, 'print', **{'new-system': 'yes'})
            if num == 33:
                bar = etree.SubElement(meas, 'barline', location='left')
                etree.SubElement(bar, 'bar-style').text = 'heavy-light'
                etree.SubElement(bar, 'repeat', direction='forward')
            if num == 53:
                bar = etree.SubElement(meas, 'barline', location='right')
                etree.SubElement(bar, 'bar-style').text = 'light-heavy'
                etree.SubElement(bar, 'repeat', direction='backward')
            if num == 1:
                attrs = etree.SubElement(meas, 'attributes')
                etree.SubElement(attrs, 'divisions').text = str(DIV)
                key = etree.SubElement(attrs, 'key')
                etree.SubElement(key, 'fifths').text = '-1'
                etree.SubElement(key, 'mode').text = 'major'
                t = etree.SubElement(attrs, 'time')
                etree.SubElement(t, 'beats').text = '3'
                etree.SubElement(t, 'beat-type').text = '4'
                etree.SubElement(attrs, 'staves').text = '2'
                for ost, ssrc in stave_map:
                    clef = 'G' if ssrc in (1, 2, 4) else 'F'
                    c = etree.SubElement(attrs, 'clef', number=str(ost))
                    etree.SubElement(c, 'sign').text = clef
                    etree.SubElement(c, 'line').text = '2' if clef == 'G' else '4'
                tempo_dir(meas)
            add_directions(meas, num, pid)
            for si, (ost, ssrc) in enumerate(stave_map):
                if si:
                    # notes of a further staff of the same part start at the same
                    # time: rewind the measure cursor first
                    b = etree.SubElement(meas, 'backup')
                    etree.SubElement(b, 'duration').text = str(int(BAR * DIV))
                emit_staff(meas, ost, ssrc, staves[ssrc][mi], num, staves,
                           syll_flags, daisy, mi)
    return root


def tempo_dir(meas):
    d = etree.SubElement(meas, 'direction', placement='above')
    dt = etree.SubElement(d, 'direction-type')
    etree.SubElement(dt, 'words').text = 'Maestoso con moto'
    dt2 = etree.SubElement(d, 'direction-type')
    met = etree.SubElement(dt2, 'metronome')
    etree.SubElement(met, 'beat-unit').text = 'quarter'
    etree.SubElement(met, 'per-minute').text = '96'
    etree.SubElement(d, 'sound', tempo='96')


def add_directions(meas, num, pid):
    for (mnum, lpid, staff, text) in LABELS:
        if mnum != num or lpid != pid:
            continue
        if text == 'Maestoso con moto':
            continue
        d = etree.SubElement(meas, 'direction', placement='above')
        dt = etree.SubElement(d, 'direction-type')
        etree.SubElement(dt, 'words').text = text
        etree.SubElement(d, 'staff').text = str(staff)
    for (mnum, dpid, staff, dyn) in DYNAMICS:
        if mnum != num or dpid != pid:
            continue
        d = etree.SubElement(meas, 'direction', placement='below')
        dt = etree.SubElement(d, 'direction-type')
        dy = etree.SubElement(dt, 'dynamics')
        etree.SubElement(dy, dyn)
        etree.SubElement(d, 'staff').text = str(staff)


def emit_staff(meas, ost, ssrc, src_meas, num, staves, syll_flags, daisy, mi):
    voices = {}
    for ev in src_meas['events']:
        voices.setdefault(ev['voice'], []).append(ev)
    # a staff that only has full-measure rests is left completely empty so that
    # MuseScore's "hide empty staves" can suppress it as in the print
    if voices and all(ev['kind'] == 'rest' and ev.get('measure_rest')
                      for evs in voices.values() for ev in evs):
        return
    if not voices:
        n = etree.SubElement(meas, 'note')
        etree.SubElement(n, 'rest')
        etree.SubElement(n, 'duration').text = str(int(BAR * DIV))
        etree.SubElement(n, 'voice').text = str((ost - 1) * 4 + 1)
        etree.SubElement(n, 'type').text = 'half'
        etree.SubElement(n, 'dot')
        etree.SubElement(n, 'staff').text = str(ost)
        return
    vlist = sorted(voices)
    for i, v in enumerate(vlist):
        if i:
            b = etree.SubElement(meas, 'backup')
            etree.SubElement(b, 'duration').text = str(int(BAR * DIV))
        voice = (ost - 1) * 4 + i + 1
        cursor = 0.0
        for ev in voices[v]:
            if ev['onset'] > cursor + 1e-6:
                emit_rest(meas, ost, voice, ev['onset'] - cursor)
            emit_event(meas, ost, voice, ssrc, ev, num, mi, syll_flags, daisy)
            cursor = ev['onset'] + ev['dur']
        if cursor < BAR - 1e-6:
            emit_rest(meas, ost, voice, BAR - cursor)


def emit_rest(meas, ost, voice, dur):
    n = etree.SubElement(meas, 'note')
    etree.SubElement(n, 'rest')
    etree.SubElement(n, 'duration').text = str(int(round(dur * DIV)))
    etree.SubElement(n, 'voice').text = str(voice)
    tn = TYPEMAP.get(round(dur, 4))
    if tn:
        etree.SubElement(n, 'type').text = tn
    etree.SubElement(n, 'staff').text = str(ost)


def emit_event(meas, ost, voice, ssrc, ev, num, mi, syll_flags, daisy):
    duration = int(round(ev['dur'] * DIV))
    if ev['kind'] == 'rest':
        n = etree.SubElement(meas, 'note')
        etree.SubElement(n, 'rest')
        etree.SubElement(n, 'duration').text = str(duration)
        etree.SubElement(n, 'voice').text = str(voice)
        if ev.get('measure_rest'):
            # a full 3/4 bar rest notated explicitly (MuseScore mis-computes the
            # measure length when fed <rest measure="yes"/>)
            etree.SubElement(n, 'type').text = 'half'
            etree.SubElement(n, 'dot')
        else:
            tn = TYPEMAP.get(ev['notated'])
            if tn:
                etree.SubElement(n, 'type').text = tn
        etree.SubElement(n, 'staff').text = str(ost)
        return
    # source corrections discovered by comparing the render with the print:
    # the OMR read the choir staff one octave too high for m.26-53
    def octave_shift(ssrc, num):
        return -12 if (ssrc == 1 and 26 <= num <= 53) else 0
    shift = octave_shift(ssrc, num)
    pairs = sorted(zip([p + shift for p in ev['pitches']],
                       ev.get('tpcs') or [-99] * len(ev['pitches'])))
    for k, (midi, tpc) in enumerate(pairs):
        n = etree.SubElement(meas, 'note')
        if k:
            etree.SubElement(n, 'chord')
        n.append(pitch_el(midi, tpc))
        etree.SubElement(n, 'duration').text = str(duration)
        if ev['tie_start']:
            etree.SubElement(n, 'tie', type='start')
        if ev['tie_end']:
            etree.SubElement(n, 'tie', type='stop')
        etree.SubElement(n, 'voice').text = str(voice)
        etree.SubElement(n, 'type').text = TYPEMAP.get(ev['notated'], 'quarter')
        for _ in range(ev['dots']):
            etree.SubElement(n, 'dot')
        if ev['tuplet']:
            tm = etree.SubElement(n, 'time-modification')
            etree.SubElement(tm, 'actual-notes').text = str(ev['tuplet'][1])
            etree.SubElement(tm, 'normal-notes').text = str(ev['tuplet'][0])
        etree.SubElement(n, 'staff').text = str(ost)
        if k == 0 and ev['articulations']:
            no = etree.SubElement(n, 'notations')
            art = etree.SubElement(no, 'articulations')
            for a in ev['articulations']:
                if a:
                    etree.SubElement(art, a)
        if k == 0:
            for li, ly in enumerate(ev['lyrics']):
                verse = verse_for(num, ly['no'])
                if verse is None:
                    continue
                text = ly['text']
                if len(text) > 2 and text[0].isdigit() and text[1:3] == '. ':
                    text = text[3:].strip()
                text = LYRIC_FIX.get((text, num), text)
                lyr = etree.SubElement(n, 'lyric', number=str(verse))
                flag = syll_flags.get((ssrc, mi, ly['no'], round(ev['onset'], 4), li))
                if flag:
                    etree.SubElement(lyr, 'syllabic').text = flag
                tx = etree.SubElement(lyr, 'text')
                tx.text = text
                if daisy:
                    tx.set('{http://www.w3.org/XML/1998/namespace}lang', 'de')


if __name__ == '__main__':
    mode = sys.argv[1]
    out = sys.argv[2]
    r = build(mode == 'daisy')
    etree.ElementTree(r).write(out, pretty_print=True, xml_declaration=True,
                               encoding='UTF-8')
    print('wrote', out)
