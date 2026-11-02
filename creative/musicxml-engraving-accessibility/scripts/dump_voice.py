#!/usr/bin/env python3
"""Stimmen-/Stand-genauer Takt-Dump einer Quelle (MusicXML oder MXL).

Aufruf:  dump_voice.py <quelle> <takt|lo-hi> [part-index 1-basiert]

Zeigt je Note: Part, Staff, Voice, Onset, Tonhoehe, Dauer, alle Lyric-Zeilen
mit ihrer number und syllabic. Damit laesst sich entscheiden, ob eine textlose
Note im Stimmauszug wirklich textlos ist (gematchte Quellstimme = Part+Staff+
Voice) oder ob nur eine andere Stimme an derselben Stelle Text hat
(Tonklassen-Fehltreffer). Ebenso: Divisi-Linien eines Drucks gegen die Quelle
pruefen (zwei Schlüssel / zwei Textzeilen = zwei Stimmen).

MXL wird über META-INF/container.xml -> rootfile/@full-path aufgelöst.
Benötigt lxml.
"""
import sys
import zipfile
from fractions import Fraction
from pathlib import Path

from lxml import etree as E


def root_of(path):
    p = Path(path)
    if p.suffix.lower() == '.mxl':
        with zipfile.ZipFile(p) as z:
            try:
                c = E.fromstring(z.read('META-INF/container.xml'))
                rp = c.find('.//rootfile')
                if rp is not None:
                    return E.fromstring(z.read(rp.get('full-path')))
            except Exception:
                pass
            for n in z.namelist():
                if n.lower().endswith(('.xml', '.musicxml')) and not n.startswith('META-INF'):
                    return E.fromstring(z.read(n))
        raise SystemExit('kein Score in MXL gefunden')
    return E.parse(str(p)).getroot()


def pit(note):
    p = note.find('pitch')
    if p is None:
        return 'Pause/Rest'
    step = p.findtext('step')
    alter = int(p.findtext('alter') or 0)
    octave = int(p.findtext('octave'))
    return f"{step}{'#' if alter > 0 else 'b' if alter < 0 else ''}{octave}"


def main():
    root = root_of(sys.argv[1])
    lo_s, _, hi_s = sys.argv[2].partition('-')
    lo = int(lo_s)
    hi = int(hi_s) if hi_s else lo
    only = int(sys.argv[3]) - 1 if len(sys.argv) > 3 else None

    for pi, part in enumerate(root.findall('part')):
        if only is not None and pi != only:
            continue
        name = root.find(f'part-list/score-part[{pi + 1}]/part-name')
        print(f"### Part {pi + 1} = {name.text if name is not None else '?'}")
        for measure in part.findall('measure'):
            try:
                num = int(measure.get('number'))
            except (TypeError, ValueError):
                continue
            if not (lo <= num <= hi):
                continue
            div = int(measure.findtext('attributes/divisions') or 0)
            if not div:
                for other in part.findall('measure'):
                    d = other.findtext('attributes/divisions')
                    if d:
                        div = int(d)
                        break
            print(f"-- Takt {num} (div={div})")
            print_measure(measure, div)


def print_measure(measure, div):
    for staff in range(1, 5):
        rows = []
        t = Fraction(0)
        for el in measure:
            if el.tag == 'backup':
                t -= Fraction(int(el.findtext('duration')), div)
                continue
            if el.tag == 'forward':
                t += Fraction(int(el.findtext('duration')), div)
                continue
            if el.tag != 'note':
                continue
            if int(el.findtext('staff') or 1) != staff:
                continue
            voice = el.findtext('voice') or '-'
            dur = Fraction(int(el.findtext('duration')), div)
            if el.find('chord') is None:
                onset = t
                t += dur
            else:
                onset = t - dur
            tags = []
            if el.get('print-object') == 'no':
                tags.append('print-object=no')
            if el.find('rest') is not None:
                tags.append('rest')
            if el.find('chord') is not None:
                tags.append('chord')
            lyrics = []
            for L in el.findall('lyric'):
                txt = ''.join(L.itertext()).strip()
                lyrics.append(f"[{L.get('number') or '?'}]{txt}({L.findtext('syllabic') or ''})")
            tail = ' '.join(lyrics) if lyrics else 'TEXTLOS'
            rows.append(f"    st{staff} v{voice} @{onset} {pit(el)} d{dur} "
                        f"{' '.join(tags)} {tail}".rstrip())
        if rows:
            print('\n'.join(rows))


if __name__ == '__main__':
    main()
