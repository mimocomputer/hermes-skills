"""Audit lyric syllables of a MusicXML/MSCZ-derived score against a German dictionary.

Rebuilds every sung word from the syllable sequence (per staff/voice/verse, in
musical order), then checks the word with hunspell (de_DE).  Reports words whose
surface form is not in the dictionary, plus a secondary check for syllables that
look like a dropped umlaut (Konig, horen, erhalt, ...).

usage: lyric_audit.py <score.musicxml> [expected-text-file]
"""
import re
import subprocess
import sys
from lxml import etree

# pre-reform / hymnal spellings that a modern dictionary rejects but the print uses
WHITELIST = {
    'vergiß', 'muß', 'daß', 'Schluß', 'Erlöser', 'lobgesungen', 'sei',
    'gepriesen', 'Halleluja', 'Amen', 'Herren', 'Adlers', 'Fittichen',
}
UMLAUT_SUSPECT = re.compile(r'^(K|k)[oy]n|hor|halt|gill|Leb|mich|fuh|sicht')


def words_from_xml(path):
    """Yield (part, staff, verse, word) rebuilt from the syllable stream."""
    root = etree.parse(path).getroot()
    for pi, part in enumerate(root.findall('part')):
        seq = {}
        for m in part.findall('measure'):
            num = int(m.get('number')) if m.get('number', '').isdigit() else 0
            for el in m.findall('note'):
                st = el.findtext('staff') or '1'
                for l in el.findall('lyric'):
                    verse = l.get('number')
                    text = (l.findtext('text') or '').strip()
                    syl = l.findtext('syllabic') or 'single'
                    extends = l.find('extend') is not None
                    key = (pi, st, verse)
                    seq.setdefault(key, []).append((num, text, syl, extends))
        for key, items in seq.items():
            word = ''
            start = None
            for num, text, syl, extends in items:
                if start is None:
                    start = num
                word += text
                if syl in ('end', 'single'):
                    yield (key[0], key[1], key[2], start, word)
                    word = ''
                    start = None
            if word:
                yield (key[0], key[1], key[2], start, word)


def hunspell_bad(words):
    if not words:
        return {}
    proc = subprocess.run(['hunspell', '-d', 'de_DE', '-i', 'UTF-8', '-l'],
                          input='\n'.join(words), capture_output=True, text=True)
    return set(proc.stdout.split())


def main(path):
    entries = list(words_from_xml(path))
    words = []
    for e in entries:
        w = e[4]
        if w.lower() in WHITELIST:
            continue
        words.append(w)
    bad = hunspell_bad(words)
    # hunspell lowercases? no: -l reports the token as given
    bad_l = {w.lower(): w for w in words if w in bad or w.lower() in {b.lower() for b in bad}}
    print(f'{len(entries)} sung words rebuilt, {len(words)} checked')
    if bad_l:
        print('dictionary rejects:')
        for e in entries:
            w = e[4]
            if w.lower() in bad_l:
                print(f'   part{e[0]+1} staff{e[1]} verse{e[2]} from m{e[3]}: {w!r}')
    else:
        print('dictionary rejects: none')
    sus = [e for e in entries if UMLAUT_SUSPECT.search(e[4])]
    if sus:
        print('umlaut/letter suspects:')
        for e in sus:
            print(f'   part{e[0]+1} staff{e[1]} verse{e[2]} from m{e[3]}: {e[4]!r}')


if __name__ == '__main__':
    main(sys.argv[1])
