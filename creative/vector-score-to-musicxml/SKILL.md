---
name: vector-score-to-musicxml
description: Use when transcribing vector PDF scores to MusicXML.
metadata:
  hermes:
    tags: [musicxml, pdf, music, transcription, musescore]
    category: creative
---

# Lightweight vector-score transcription

Use for licensed/user-supplied vector music PDFs when heavy OMR is unavailable. Load musicxml-engraving-accessibility and pdf skills as well. Do not assume a successful MusicXML import proves musical accuracy.

1. Inspect PDF `pymupdf` rawdict character origins, font names and glyph counts, and `get_drawings()` paths. Persist page-wise raw characters, spans and vectors plus source PNGs before inference. Maestro often exposes noteheads `œ`, `˙`, `w`, rests `∑`, `Ó`, `Œ`, `‰`, flags `j`/`J`, dynamics `P`=mp and `F`=mf; calibrate against a rendered source, never assume another font has this mapping.
2. Detect five long horizontal staff lines and calculate half-space distance. Determine clef and map glyph **origin** y, not bounding-box center, to pitch. Note bounding boxes include font ascender padding. Assign glyphs to the nearest staff across the entire page, not just a local system: ledger notes from the previous system otherwise leak into the next.
3. Detect barlines by matching the exact bottom staff boundary. Long note stems can cross all five staff lines; length alone confuses stems with barlines. Merge the two strokes of a double/final bar. Exclude courtesy time signatures after the final real measure.
4. Obtain rhythm from head shape, touching stems, flags, filled straight-sided beam polygons and augmentation dots. Cluster small x offsets in octave/chord heads, but inspect any reversed-second notes. Never infer note lengths from horizontal spacing alone.
5. Check every chord's head glyph types and distinct stems, even when its measure duration sum already looks correct. Dotted-whole chords beneath dotted-half melody notes can pass a naive measure sum test while silently shortening the chord. Separate simultaneous rhythmic layers into voices and verify each voice clock. Shared-head unisons may need two singer voices for accessibility; disclose if retained as one printed notehead.
6. Persist unresolved rhythm discrepancies and source-check them visually. Encode tuplets with real time modification. Retain actual incomplete pickup/final bars as implicit and document them; do not pad or change a signature just to make clocks fit.
7. Recover ties/slurs from filled Bezier shapes and notehead endpoints. A tie needs equal pitch AND temporal adjacency. Recover cross-system ties only when both printed curve halves agree. Keep matching evidence and flag unproofread curve associations.
8. Extract lyrics from original text spans, excluding staff labels, harmony symbols and directions. Split internal syllable gaps within a span when engraving spacing spans multiple notes. Sort raw characters by x and exclude separately drawn hyphens before reconstructing these chunks; otherwise a late-drawn hyphen shrinks the chunk bbox and joins syllables onto the wrong note. Encode Korean/phonetic rows separately and carry syllabic state across system boundaries.
9. Validate MusicXML `type`, dots and tuplet ratio against numeric duration. A missing dotted-whole duration mapping with a fallback quarter type can be accepted by MuseScore but imported as a much shorter note. Do not default unknown durations to quarter: fail visibly.
10. Import into the user's requested MuseScore version, export MusicXML again, and compare canonical part/staff/pitch/onset/duration multisets. Divisions can change on export, so normalize rational durations. Compare measure ordinal for implicit measures because MuseScore may export an internal X1 number. Render an actual PDF and visually inspect source-comparable systems.
11. Verify every source notehead is accounted for, page by page, programmatically. Separate this coverage assertion and exact roundtrip verification from an editorial accuracy claim. Report remaining lyric, curve, voice-identity and repeat-playback uncertainty honestly.

Native MuseScore 4 MSCZ stores its style in `score_style.mss`, not necessarily an embedded `Style` node in MSCX. To restore source hide-empty systems, read existing style properties `hideEmptyStaves` and `dontHideStavesInFirstSystem`, then change them to 1 and 0 respectively; keep parts and their rests rather than deleting music. Re-import/export after any native change and verify notes are unchanged.
