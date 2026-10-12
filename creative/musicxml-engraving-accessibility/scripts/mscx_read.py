"""Read the OMR .mscx into a structured model with exact onsets.

Returns: {staff_id: [measure, ...]} where measure = {
    'number': str, 'events': [event, ...], 'len': float (quarters),
    'startRepeat': bool, 'endRepeat': bool, ...
}
event = {'kind','voice','onset','dur','notated','dots','tuplet','pitches',
         'lyrics','tie_start','tie_end','articulations','head','stem'}
"""
import xml.etree.ElementTree as ET

DIV = 480.0
DUR = {'whole': 4.0, 'half': 2.0, 'quarter': 1.0, 'eighth': 0.5, '16th': 0.25,
       '32nd': 0.125, '64th': 0.0625, '128th': 0.03125, '256th': 0.015625,
       'breve': 8.0, 'longa': 16.0, '512th': 0.0078125}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
BAR = 3.0  # 3/4 in quarter notes


def spname(midi):
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def read(path):
    root = ET.parse(path).getroot()
    blocks = [s for s in root.iter('Staff') if s.find('Measure') is not None]
    staves = {}
    for s in blocks:
        sid = int(s.get('id'))
        base = (sid - 1) * 4
        measures = []
        first_number = s.find('Measure').get('number')
        mlen = float(first_number) if first_number.isdigit() else 1.0
        mstart = (float(first_number) - 1.0) * DIV * BAR if first_number.isdigit() else 0.0
        for m in s.findall('Measure'):
            tups = {}
            for t in m.findall('Tuplet'):
                tups[t.get('id')] = (int(t.findtext('normalNotes') or 2),
                                     int(t.findtext('actualNotes') or 3))
            events = []
            cursor = {}
            pending_tick = None
            for el in m:
                if el.tag == 'tick':
                    pending_tick = float(el.text)
                    continue
                if el.tag not in ('Chord', 'Rest'):
                    continue
                tr = el.findtext('track')
                voice = (int(tr) - base) if tr is not None else 0
                dt = el.findtext('durationType')
                tp = None
                if dt == 'measure':
                    notated, dots = 4.0, 0
                    d_override = BAR
                else:
                    d_override = None
                    notated = DUR.get(dt, 1.0)
                    dots = int(el.findtext('dots') or 0)
                    tref = el.findtext('Tuplet')
                    if tref:
                        tp = tups.get(tref)
                d = notated
                add = notated / 2
                for _ in range(dots):
                    d += add
                    add /= 2
                if tp:
                    d = d * tp[0] / tp[1]
                if d_override is not None:
                    d = d_override
                if pending_tick is not None:
                    onset = (pending_tick - mstart) / DIV
                    pending_tick = None
                else:
                    onset = cursor.get(voice, 0.0)
                pitches = [int(n.findtext('pitch')) for n in el.findall('Note')
                           if n.findtext('pitch')]
                tpcs = [int(n.findtext('tpc') or -99) for n in el.findall('Note')
                        if n.findtext('pitch')]
                lyrics = []
                for ly in el.findall('Lyrics'):
                    lyrics.append({
                        'no': int(ly.findtext('no') or 0),
                        'text': (ly.findtext('text') or ''),
                        'syllabic': (ly.findtext('syllabic') or ''),
                    })
                tie_start = any(n.find('Tie') is not None for n in el.findall('Note'))
                tie_end = any(n.find('endSpanner') is not None for n in el.findall('Note'))
                arts = [a.findtext('subtype') for a in el.findall('Articulation')]
                events.append({
                    'kind': 'rest' if el.tag == 'Rest' else 'chord',
                    'measure_rest': dt == 'measure',
                    'voice': voice, 'onset': onset, 'dur': d, 'notated': notated,
                    'dots': dots, 'tuplet': tp, 'pitches': pitches, 'tpcs': tpcs,
                    'lyrics': lyrics, 'tie_start': tie_start, 'tie_end': tie_end,
                    'articulations': arts,
                    'head': el.findtext('Head') or '',
                    'stem': el.findtext('StemDirection') or '',
                })
                if dt == 'measure':
                    cursor[voice] = BAR
                else:
                    cursor[voice] = onset + d
            mlen = max([BAR] + [e['onset'] + e['dur'] for e in events])
            measures.append({
                'number': m.get('number'), 'events': events, 'len': mlen,
                'startRepeat': m.find('startRepeat') is not None,
                'endRepeat': m.find('endRepeat') is not None,
                'barlines': [b.findtext('subtype') for b in m.findall('BarLine')],
                'texts': [t.findtext('text') for t in m.findall('StaffText')],
                'dynamics': [d.findtext('subtype') for d in m.findall('Dynamic')],
                'hairpins': [h.findtext('subtype') for h in m.findall('HairPin')],
                'keysig': m.find('KeySig') is not None,
                'timesig': m.find('TimeSig') is not None,
            })
            mstart += mlen * DIV
        staves[sid] = measures
    return staves
