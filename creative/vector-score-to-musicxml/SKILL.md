---
name: vector-score-to-musicxml
description: Use when transcribing vector PDF scores to MusicXML.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [musicxml, pdf, music, transcription, musescore]
    category: creative
---

# Lightweight vector-score transcription

## When to Use

Use for licensed/user-supplied vector music PDFs when heavy OMR is unavailable. Load musicxml-engraving-accessibility and pdf skills as well. Do not assume a successful MusicXML import proves musical accuracy.

1. Inspect PDF `pymupdf` rawdict character origins, font names and glyph counts, and `get_drawings()` paths. Persist page-wise raw characters, spans and vectors plus source PNGs before inference. Maestro often exposes noteheads `œ`, `˙`, `w`, rests `∑`, `Ó`, `Œ`, `‰`, flags `j`/`J`, dynamics `P`=mp and `F`=mf; calibrate against a rendered source, never assume another font has this mapping.
2. Detect five long horizontal staff lines and calculate half-space distance. Determine clef and map glyph **origin** y, not bounding-box center, to pitch. Note bounding boxes include font ascender padding. Assign glyphs to the nearest staff across the entire page, not just a local system: ledger notes from the previous system otherwise leak into the next.
3. Detect barlines by matching both an actual staff-top boundary and the exact bottom staff boundary. A note stem can coincidentally end at the bottom staff line; the bottom-boundary test alone creates false bars. Merge double/final strokes using calibrated source spacing, and exclude courtesy signatures after the final real measure.
   - Deduplicate touching beam polygons by their interpolated vertical level at the stem, not polygon count: a left and right beam segment can meet on the same stem without forming a sixteenth-note beam.
   - Inspect all notehead font sizes and vector-only shapes. Reduced-size noteheads can be grace notes, while circled cross half-note heads can be vector drawings absent from the music-font character census. A glyph-only total is not an ink-notehead total.
   - Use stem geometry to review ledger-note staff assignment, but do not blindly replace notehead proximity with stem-midpoint proximity: dense piano chords and cross-staff engraving can invalidate either heuristic.
4. Obtain rhythm from head shape, touching stems, flags, filled straight-sided beam polygons and augmentation dots. Cluster small x offsets in octave/chord heads, but inspect any reversed-second notes. Never infer note lengths from horizontal spacing alone.
5. Check every chord's head glyph types and distinct stems, even when its measure duration sum already looks correct. Dotted-whole chords beneath dotted-half melody notes can pass a naive measure sum test while silently shortening the chord. Separate simultaneous rhythmic layers into voices and verify each voice clock. Shared-head unisons may need two singer voices for accessibility; disclose if retained as one printed notehead.
6. Persist unresolved rhythm discrepancies and source-check them visually. Encode tuplets with real time modification. Retain actual incomplete pickup/final bars as implicit and document them; do not pad or change a signature just to make clocks fit.
7. Recover ties/slurs from filled Bezier shapes and notehead endpoints. A tie needs equal pitch AND temporal adjacency. Recover cross-system ties only when both printed curve halves agree. Keep matching evidence and flag unproofread curve associations.
8. Extract lyrics from original text spans, excluding staff labels, harmony symbols and directions. Split internal syllable gaps within a span when engraving spacing spans multiple notes. Sort raw characters by x and exclude separately drawn hyphens before reconstructing these chunks; otherwise a late-drawn hyphen shrinks the chunk bbox and joins syllables onto the wrong note. Encode Korean/phonetic rows separately and carry syllabic state across system boundaries.
9. Validate MusicXML `type`, dots and tuplet ratio against numeric duration. A missing dotted-whole duration mapping with a fallback quarter type can be accepted by MuseScore but imported as a much shorter note. Do not default unknown durations to quarter: fail visibly.
10. Import into the user's requested MuseScore version, export MusicXML again, and compare canonical part/staff/pitch/onset/duration multisets. Divisions can change on export, so normalize rational durations. Compare measure ordinal for implicit measures because MuseScore may export an internal X1 number. Render an actual PDF and visually inspect source-comparable systems.
11. Treat imported playback tempos as potentially converter defaults rather than source evidence. PDFtoMusic-based workflows have documented a default of 80 (https://github.com/stubiedoobiedoo/pdf-omr-pmerge#known-issues-and-solutions); confirm the user's version/export before asserting this universally. Inspect printed tempo, PDF metadata/attachments and the actual MusicXML metronome/sound tags separately. A plausible playback speed does not prove a tempo was encoded in the PDF.
12. Verify every source notehead is accounted for, page by page, programmatically. Separate this coverage assertion and exact roundtrip verification from an editorial accuracy claim. Report remaining lyric, curve, voice-identity and repeat-playback uncertainty honestly.

## Opus-font and export pitfalls

- Calibrate Opus separately from Maestro: OpusStd can expose sixteenth rests as `≈`, sixteenth flags as `r`/`R`, spoken cross noteheads as `¿`, and augmentation dots as OpusSpecialStd `™`. A flag origin need not coincide with the stem endpoint; inspect actual offsets. Treat cross heads as spoken/unpitched notation, not evidence of a prescribed sung pitch, and disclose any positional pitch used for MIDI.
- Preserve explicit lyric spaces as segmentation boundaries. Exclude proven tie-stop continuations when assigning a new syllable: a long, left-aligned word can otherwise map to the second tied head. Match lyric extension rules to the exact lyric baseline and text-right edge, not a loose below-staff band that also contains ledger lines.
- Inventory every source cubic curve piece. Pair both halves across system breaks, accounting for curves that end several points before a double bar; include cross-system slurs with changing pitch, not just equal-pitch ties. Stem-side slur endpoints can be substantially farther from the head than tie endpoints. Persist matches and audit unassigned pieces rather than widening tolerances without review.
- Detect paired diagonal wedge strokes and double-bar stroke clusters explicitly; neither appears in a notehead census. A nearest-staff rule alone can misassign dynamics printed between lyrics and the following staff; source-check these exceptions.
- Respect the user's harmony-playback preference; Julian wants native Harmony playback explicitly enabled (`<play>1</play>`). Disable it only when requested or when analysis-only treatment has been agreed. Audit automatic chord-channel events separately from notated tied-note attacks, because MuseScore can synthesize hundreds of additional chord notes. MuseScore may also omit terminal silent measures; retain the untouched export as evidence, extend only end-of-track deltas to the verified score duration, and recheck note events unchanged.
- Set MusicXML page defaults and explicit credit types before relying on credit placement. Recheck the native title frame: imported poet/lyricist alignment can overlap the title even when MusicXML positions differ.
- Recover the music-font beat-unit glyph beside every numeric tempo rather than assuming quarter BPM: Maestro `h` is a half note, so half=126 requires `sound tempo=252`. A text-span split across a bar can misassign the closing tempo fragment; source-check and encode a real metronome object.
- Export long native scores one format at a time with a subprocess timeout and individual logs; an interrupted multi-output batch does not establish that its outputs exist or are valid.
- Preserve authoritative MusicXML separately when MuseScore turns `unpitched` spoken crossheads into positional pitched notes. Report this semantic roundtrip exception explicitly; notehead/onset/duration equality is not unpitched identity. Normalize documented piano voice renumbering separately from musical differences.

Native MuseScore 4 MSCZ stores its style in `score_style.mss`, not necessarily an embedded `Style` node in MSCX. To restore source hide-empty systems, read existing style properties `hideEmptyStaves` and `dontHideStavesInFirstSystem`, then change them to 1 and 0 respectively; keep parts and their rests rather than deleting music. Re-import/export after any native change and verify notes are unchanged.
