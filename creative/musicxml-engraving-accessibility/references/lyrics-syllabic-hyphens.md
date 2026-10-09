# Lyrics: syllabic markup and the literal-hyphen defect

## Rule

A syllable-separating hyphen belongs ONLY in the `<syllabic>` element, never in `<text>`.

- `single` – whole word on one note.
- `begin`   – first syllable of a multi-syllable word (hyphen drawn after it).
- `middle`  – hyphen drawn before and after.
- `end`     – last syllable of the word (hyphen drawn before it).

MuseScore (and any notation editor) draws the hyphen itself from the syllabic flag.
Typing `-` while entering lyrics jumps to the next note and is NOT stored in the text;
the flag is stored separately. Consequently:

- `<text>Blu-</text>` renders as `Blu-` PLUS the editor's own hyphen (`Blu--`/stray dash),
  and a braille translator sees a hyphen character inside the syllable.
- OMR / untrained transcription pipelines routinely copy the PRINTED hyphen into `<text>`
  (e.g. `Le-`, `-bens-`, `-klang`). Always audit for it.

## Detection

Any `<text>` whose content starts or ends with `-` is defective. Check the whole score:

```python
import re, zipfile
xml = zipfile.ZipFile(path).read('score.xml').decode('utf-8')
bad = [t for t in re.findall(r'<text>(.*?)</text>', xml, re.S) if '-' in t]
```

## Re-deriving `<syllabic>` from the (printed) hyphen pattern

The hyphen position in the defective source is the transcription's own statement of word
structure, so it is the ground truth for the repair. Walk each voice's lyric sequence
(part + voice + `lyric/@number`) in document order; for each syllable look at whether the
original text had a leading and/or trailing hyphen:

```
leading and trailing  -> middle
leading only          -> end
trailing only         -> begin
neither               -> end   if the PREVIOUS syllable had a trailing hyphen
                         single otherwise
```

The last clause handles a continuation syllable printed without its own leading hyphen
(e.g. `Le-` `bens-` `klang`). It assumes word runs are contiguous in the voice; when they
are not (humming `mm` syllables, a missing syllable) apply a targeted exception – a syllable
that is a standalone printed word after such a gap stays `single`.

Strip the hyphens from `<text>` (`txt.strip('-')`) while recomputing the flag. Operate on the
raw XML with a regex so element order/attributes and the rest of the file are untouched.

## Verification (do all three)

1. No `<text>` contains a hyphen; counts of `<text>` and `<syllabic>` unchanged.
2. Round-trip through MuseScore (`musescore4 -o out.musicxml in.mxl`) and confirm the exported
   `<text>` is hyphen-free and the `begin/middle/end/single` values survive unchanged.
3. Render (`musescore4 -o out.pdf in.mxl`) and read the pages: the editor must draw single
   hyphens between syllables (`Blu-me`, `er-in-nern`) with no doubled/stray dash.

## Cross-check the structure

After the repair, flag any voice where a `begin` has no following `middle`/`end`, or an `end`
has no preceding `begin`/`middle`. Such a run is either a real transcription gap (a missing
syllable/note) or a wrong flag; report it rather than silently inventing the missing text.
