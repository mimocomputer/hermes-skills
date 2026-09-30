# Workflow: Bilingual Lyric Alignment & OMR Cleaning for MusicXML

When correcting an MXL file where an automated OMR pass missed one language or contaminated lyric syllables with musical markings:

### 1. Cleaning Contaminated Lyrics
- OMR engines frequently misclassify expressive text as lyrics. Scan `<lyric>` text for:
  - Tempo & agogic markings: `poco`, `a tempo`, `Largamente`, `rit.`, `ritenuto`, `accelerando`, `fine`, `al fine`
  - Dynamic indications: `p`, `mp`, `mf`, `f`, `pp`, `dim.`
  - Scan artifacts: `____`, `---`, spurious OCR letters (`tmes` -> `times`, `turne` -> `turned`)
- Treat suspicious strings as review candidates, not automatic replacements: verify sung wording and note attachment against the source before repairing a suspected OCR letter or moving an ambiguous word.
- Convert confirmed tempo/agogic terms to genuine `<direction><direction-type><words>...</words></direction-type></direction>` nodes attached to the appropriate measure.

### 2. Multi-Language (Bilingual) Encoding
- Never interleave languages by switching `<voice>` or abusing `<lyric number="1">`.
- Use consistent verse layers:
  - `<lyric number="1">`: Primary edition language (e.g. German translation)
  - `<lyric number="2">`: Secondary / original language (e.g. English original)
- For every syllable:
  - `<syllabic>` must strictly be `begin`, `middle`, `end`, or `single`.
  - Tied notes that continue a syllable should receive `<extend />` on the initial note rather than duplicate empty lyric tags on the tied-to notes.

### 3. Pronunciation Guides and Shared Choral Text

For a sung language with a separate phonetic row, retain the main sung text as row 1 and the pronunciation guide as row 2 throughout the passage. Inspect each row transition: adjacent staff lyrics or editorial text can cause a geometry extractor to shift the final syllable into rows 2/3. Set `xml:lang` on each lyric `<text>`, and optionally use lyric `name` to explain that the second row is a pronunciation guide rather than a second verse.

Where the source supplies explicit phonetic hyphens for the same sung syllables, use them as evidence for grouping the corresponding main-language syllables; do not join across printed word boundaries. Compare lyric tuples by part, measure, onset, row, text and syllabic value after export, because unchanged note pitches do not verify lyric identity.

For shared upper/lower choir words, map each source syllable to a sounding lower-staff note at the same confirmed onset. Skip rests and passages singing different vowels or text. Avoid duplicating the same syllable on each note of a tied or melismatic continuation. Strip a printed footnote marker from the accessibility edition's sung text only after retaining its exact explanation elsewhere; keep the original edition separate.

### 4. Incomplete Measure Handling

When the first bar is a pickup, preserve the edition's actual measure label (which may be 0 or 1) and set `implicit="yes"` consistently across the affected parts. Do not assume a fixed pickup-number convention or promise that this attribute alone controls every editor's numbering.

If the closing bar is genuinely short in the source, preserve its actual duration as an explicit irregular/implicit bar and report the discrepancy with the prevailing meter. Do not pad it or introduce an unsourced time signature simply to make a validator happy. An editor may export such a bar with a label like X1; verify it by ordinal and musical duration as well as its displayed source number.
