# Vector Score Transcription and MuseScore Export Verification

Use this recipe for PDF-to-MusicXML work when the PDF contains music-font glyphs and drawing paths. It complements the main skill’s always-on delivery gates; it is not a guarantee that every printed score can be parsed automatically.

## 1. Discover source structure and prepare tools

- Use `pdfinfo` and `pdftotext -layout` for initial page/text inspection, then PyMuPDF `page.get_fonts()`, `page.get_text('rawdict')` and `page.get_drawings()` to determine whether notes are vector data or raster images. Render source pages with PyMuPDF or `pdftoppm` for musical inspection.
- Install PDF utilities when needed: `sudo apt-get install --no-install-recommends poppler-utils qpdf tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu`. Use Tesseract for text, not as a substitute for optical music recognition.
- Create a durable project environment: `uv venv <project>/.venv` and `uv pip install --python <project>/.venv/bin/python pymupdf lxml mido`. Keep source PDF, raw extraction, resolved events and scripts alongside it; temporary preview images can live in the configured scratch directory.
- Discover the requested MuseScore release from the official repository, e.g. `gh api repos/musescore/MuseScore/releases/latest --jq '{tag_name,assets:[.assets[]|{name,browser_download_url,digest}]}'`. Confirm the tag is the requested major version and choose the host architecture. Verify the downloaded asset with `sha256sum` against the release digest before execution.
- For a server AppImage, use `chmod +x <image>` followed by `<image> --appimage-extract`, then retain `squashfs-root/` intact. Prefer `xvfb-run -a <installation>/squashfs-root/AppRun --version` when the offscreen plugin is not sufficient. Install Xvfb/xauth and the launcher’s identified library dependencies as necessary. Exercise `-o <probe>.pdf <probe>.musicxml` and `-o <probe>.mscz <probe>.musicxml`; version output alone does not test engraving.

## 2. Map systems before reconstructing notes

Build a machine-readable index of PDF page, printed page, system start/end measures, staff tops, barline x coordinates, clefs and active part/staff combinations. Include meter/key changes, rehearsal labels, repeat destinations and solo transitions. Hide-empty source systems can change the staff count; do not map parts merely by vertical ordinal throughout the document.

Associate each extracted notehead with its source page and x/y position. Derive diatonic pitch from calibrated staff-line spacing and current clef, then apply key signatures and actual accidentals. Determine duration from head type, stems, flags, beam levels and augmentation dots. Store unresolved events rather than forcing them to fit.

Separate simultaneous rhythmic lanes where stem directions or mixed notehead types indicate different voices. A shared-stem chord stack and independent polyphony are not interchangeable. Sum durations per lane against the prevailing meter; a balanced clock is a necessary check, not evidence that a particular rhythm is correct. Inspect suspect measures before adding tuplets, rests or altered durations.

Preserve printed irregular closing bars without padding or inventing a time signature. Use explicit implicit/irregular-bar encoding, retain source numbering, and report any different internal measure identifier the editor produces.

## 3. Recover text, curves and metric relationships

- Match curve endpoints to real notes, preserving separate ties and outer phrase/melisma slurs. Equal adjacent pitches can support a tie; different pitches require a slur. Recover cross-system ties only when both source halves and the note continuity support them. Geometry may miss a long outer slur even when all short ties were found; inspect melismas independently.
- Keep lyric attachment, syllabic groups and row identity stable across systems. Review broad PDF spans that contain multiple engraved syllables and normalize text ligatures only without changing sung wording. Use the bilingual reference for language/phonetic details.
- Inspect tempo equations at high resolution. Verify flag, dot and notehead on each side rather than accepting an independent reviewer’s prose summary. Encode note-to-note relations with `metronome/beat-unit` and `beat-unit-dot`, and numeric playback with quarter-note BPM in `sound/@tempo`.
- Preserve exact source footnote wording and reference markers in the original-faithful edition. In the accessibility edition, keep non-sung footnote symbols out of lyric syllables but encode the exact explanation as a properly anchored editorial/staff note at the relevant note or measure. Metadata and an accompanying report are supplementary, not substitutes for a navigable score annotation. Do not invent a missing alternative lyric or silently replace the original sung words. Inspect the final native and MusicXML files to verify where markers and explanations actually landed; distinguish file presence from screen-reader accessibility, which requires its own test.

## 4. Proofread and canonicalize the result

Render after each manageable page block and compare by measure, not merely by PDF page position. Assign independent review blocks where useful, require concrete part/measure/note corrections and evidence crops, and re-open the source before applying uncertain findings.

Maintain separate checks:

1. Source coverage: notehead totals per source page, including each chord tone.
2. Structure: official MusicXML XSD plus measure durations, backup/forward cursor validity and voice overlap checks.
3. Roundtrip notes: a multiset of `(part, measure ordinal, staff, rational onset, rational duration, step, alter, octave)` before and after MuseScore import/export. Use ordinal for comparisons when an implicit bar is exported with an internal label such as X1.
4. Roundtrip lyrics: `(part, measure ordinal, staff, onset, row, text, syllabic)`. Chord-note reordering need not change syllable placement, so compare by musical onset rather than solely by which chord note carries the XML lyric.
5. Musical review: full-system source/render comparison and enlarged checks of uncertain pitches, lyrics, slurs and rhythmic layers. Describe the actual depth of this review; coverage and roundtrip equality do not establish source accuracy by themselves.

## 5. Restore semantic navigation when necessary

Inspect the native MSCZ ZIP rather than assuming MusicXML sound cues became playable jumps. Read its `.mscx` and preserve all other archive entries, including `score_style.mss`.

When an imported segno/coda/D.S. is plain StaffText, replace its top-staff lookalike with palette-equivalent native objects:

- `Marker`: explicit `<track>0</track>`, style `repeat_left` or `repeat_right`, `<text>` with a standard `<sym>` where applicable, a unique `<label>`, and `<markerType>`.
- Marker types: `segno` for segno; `coda` for To Coda; `codab` for the coda destination. Do not confuse the To Coda stopping point with the destination label.
- `Jump`: explicit track zero, style `repeat_right`, source instruction text, and matching `<jumpTo>`, `<playUntil>`, `<continueAt>` labels. Preserve the chosen repeat policy with `<playRepeats>`.

Consult the matching installed/release source serializer when native XML details are uncertain rather than guessing tag spelling. Appending a marker after a polyphonic measure can otherwise inherit the last voice’s track and become invisible to repeat control.

If shared cues must be displayed on lower staves, use proper non-top system-object tracks and verify that they do not create extra playback traversals. MuseScore’s repeat list excludes non-top system objects, but this is a version-sensitive implementation detail: test the actual export.

Export `-o <score>.mid <score>.mscz`, parse with mido and compare total ticks and repeated passage boundaries to the independently computed unfolded measure order. Account only for a tiny final end-of-track tick, not whole missing beats. Validate tempo events as well as overall length.

## 6. Match original layout without hiding source labels

- Apply source system/page endings and no-break markers for intervening measures in native `LayoutBreak` objects. Page size, staff spacing and lyric minimum distance must still permit readable engraving; matching page count alone is insufficient.
- Configure native hide-empty-staves behavior to suppress absent source parts without adding playback notes. Keep original staff combinations, labels and printed page offset. In native serialization, `page-offset` controls the printed page-number offset.
- Inspect linked system-object duplicates before suppressing repeated rehearsal boxes. A label anchored to a hidden top staff may need its visible linked copy on the active solo staff. Keep the hidden top master visible when needed for propagation, and suppress only unwanted lower copies; otherwise the source’s sole visible rehearsal box can disappear. Re-render that exact page to verify the change.
- Replace end-of-measure navigation StaffText with actual right-aligned jump/marker objects instead of dragging its appearance left; an annotation anchored at the next measure can extend beyond the page.
- Separate descriptive tempo words from a single numeric metronome indication. Use multiline copyright text or smaller footer text when necessary; a long one-line rights field can clip outside a narrow source-sized page.

## 7. Package the exact verified artifacts

Keep original and adapted editions separate. Run confirmed source corrections before adaptation on every rebuild. After the final edit, export both PDFs, rerun roundtrip and playback checks, and refresh any bounds report before archiving.

Package compressed MusicXML using `META-INF/container.xml` pointing to the actual root score; verify ZIP integrity and equality of its embedded score to the authoritative XML. Open the MXL with MuseScore as an interoperability smoke test. Preserve the authoritative XML because native editor export can drop language or editorial metadata.

Provide original/adapted MSCZ and MXL, optional uncompressed XML, PDFs, MIDI and a readable limitations report. A bundle manifest with per-file SHA-256 makes the tested handoff identifiable. Send individual editable files as well as the bundle, with a concise statement of what was verified and what still needs musical or assistive-technology review.
