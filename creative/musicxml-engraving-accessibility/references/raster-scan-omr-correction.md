# Raster scans and OMR correction

Depth for scores supplied as a scanned PDF plus an OMR-generated project file (`.mscz`/`.mxl`). The scan is the authority; the OMR file is a draft to correct. Companion to [Vector score transcription](vector-score-transcription.md).

## 1. Classify the source

```python
import pymupdf
d = pymupdf.open('source.pdf')
for p in d:
    print(p.number, p.get_fonts(), len(p.get_drawings()),
          p.get_images(full=True), repr(p.get_text()[:200]))
```

No fonts, no text, one large image per page → raster scan. The embedded image size (e.g. 1241×1755 for A4 at 150 dpi) is the detail ceiling: a crop rendered at 900 dpi holds the same information. Record it, and derive the printed scale from the staff lines (section 3) because that scale is needed later to reproduce the engraving.

## 2. Reading crops that are actually legible

- Threshold the overlay away: keep ink below ~150–170 grey, everything else white. Grey watermarks and page show-through vanish, the music stays.
- Keep each crop near the vision downscale limit (~1 MPix). Good shapes: 1–3 measures across the full system width at 400–500 dpi; a single staff only, at 800–1200 dpi, when pitch placement or ledger lines are in doubt.
- Crop by page fractions, not absolute coordinates, so one recipe works on every page. `scripts/clean_crop.py` does both.
- Read the printed measure numbers; the OMR's layout is not authority for bar numbering.

## 3. Locate systems, staves and barlines

- **Staff lines:** rows whose dark-pixel count exceeds ~0.45 × page width, grouped; five evenly spaced rows = one staff; consecutive groups = one system. Store the line rows — every crop, pitch mapping and barline search hangs off them.
- **Pitch mapping:** staff space = (last_line − first_line) / 8. Steps downward from the top line: treble top line F5, bass top line A3 (e.g. three half-spaces below F5 = C5).
- **Barlines:** columns whose ink is unbroken from the top line of the system's first staff to the bottom line of its last staff. A run spanning one staff height is a stem — a cheaper row-threshold search returns stems and beams by the dozen.
- **Noteheads:** horizontal erosion or ellipse-template correlation gives objective pitch-class evidence, but staff-line removal splits noteheads sitting on a line and clefs/text create false positives. Corroborate, never transcribe from it alone.

## 4. Validate the OMR project before reading it

A MuseScore `.mscz` is a zip: `META-INF/container.xml` points at the root `.mscx` (alongside `score_style.mss` and thumbnails).

- `<Division>` = ticks per quarter (commonly 480).
- Durations: `<durationType>` names (`whole` … `512th`, or `measure`), with `<dots>N</dots>` — not `<Dot/>`.
- Tuplets: a `<Tuplet id="…">` definition with `<normalNotes>`/`<actualNotes>` lives in the measure and is referenced by `<Tuplet>N</Tuplet>` on each chord; multiply the notated duration by normal/actual.
- `<tick>` gives absolute onsets (measure start = (number − 1) × bar length); `<track>` marks a voice change, `(staff − 1) × 4 + voice`.
- **Validation:** sum durations per measure per voice and require the prevailing meter. Flag voices that end early — inner voices in OMR output are often left short at a repeat or cadence — and drop a trailing extra measure that follows the final barline.
- Do **not** validate against the editor's MusicXML re-export: importing a MuseScore-2-era OMR file into Studio 4 can flatten two staves into one voice stream and render measures over-full although the native file is valid.
- **Lyrics:** `<Lyrics><no>N</no>` is the verse row; the printed verse number is glued into the text as `"1. Lo"` and must be split off into `<verse>`; `<syllabic>` is missing on many single-syllable words and must be re-derived from the word structure. Diff the sung text against the scan — OMR engines drop umlauts and single letters ("Ko" for "Kö", "mich" for "mäch", "Leb" for "Lob", "hor" for "hö", "fuh" for "füh", "gill" for "giß").
- **Directions:** staff/system texts and section labels ("Tpts.", "Org.", "v. 2: CHOR und ORGEL", "SOPRANEN") are mostly absent from OMR output; take them from the scan, including which staff and which system they belong to. Read the printed tempo symbol and its dot from an enlarged crop before trusting the OMR's BPM — MusicXML `sound/@tempo` is quarter-note BPM.

## 5. Order of work

1. Classify the source; record staff-line geometry and the printed scale.
2. Validate OMR structure measure by measure (tuplets applied); repair short voices, drop spurious trailing measures.
3. Build the corrected MusicXML, force the printed system/page breaks, render to PDF.
4. Compare render against scan system by system — this is where octave shifts, displaced bar-line content, shifted syllables and dropped accidentals surface.
5. Fix, re-render, repeat; then package both editions with the uncertainty report.

Reading every bar out of crops before step 3 exists is the failure mode: coordinate bookkeeping eats the session and the deliverable slips. Keep the durable project tree (`source/ work/ out/ scripts/ report/`) and write each probe as a small re-runnable script under `scripts/`.
