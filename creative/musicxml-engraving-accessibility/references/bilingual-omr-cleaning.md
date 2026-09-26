# Workflow: Bilingual Lyric Alignment & OMR Cleaning for MusicXML

When correcting an MXL file where an automated OMR pass missed one language or contaminated lyric syllables with musical markings:

### 1. Cleaning Contaminated Lyrics
- OMR engines frequently misclassify expressive text as lyrics. Scan `<lyric>` text for:
  - Tempo & agogic markings: `poco`, `a tempo`, `Largamente`, `rit.`, `ritenuto`, `accelerando`, `fine`, `al fine`
  - Dynamic indications: `p`, `mp`, `mf`, `f`, `pp`, `dim.`
  - Scan artifacts: `____`, `---`, spurious OCR letters (`tmes` -> `times`, `turne` -> `turned`)
- Convert tempo/agogic terms to genuine `<direction><direction-type><words>...</words></direction-type></direction>` nodes attached to the appropriate measure.

### 2. Multi-Language (Bilingual) Encoding
- Never interleave languages by switching `<voice>` or abusing `<lyric number="1">`.
- Use consistent verse layers:
  - `<lyric number="1">`: Primary edition language (e.g. German translation)
  - `<lyric number="2">`: Secondary / original language (e.g. English original)
- For every syllable:
  - `<syllabic>` must strictly be `begin`, `middle`, `end`, or `single`.
  - Tied notes that continue a syllable should receive `<extend />` on the initial note rather than duplicate empty lyric tags on the tied-to notes.

### 3. Upbeat (Anacrusis) Handling
- When the first bar is incomplete (e.g. 3 eighths in a 4/4 measure):
  - Mark `<measure number="1" implicit="yes">` across all parts.
  - This prevents braille transcribers and notation software from offsetting all subsequent measure numbers by +1.
