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

## 6. OMR engines (only when the user has supplied no OMR export)

The default source of a raster note base for this user is **his own Halbestunde/MuseHub export**, not a locally run engine. Run local OMR only to get a second, independent reading: a disagreement between the two drafts localises exactly which measures need an enlarged-crop decision.

**Audiveris 5.11.0, built from source (verified on Ubuntu 26.04 aarch64):** releases ship only x86_64/macOS/Windows assets, so on ARM it must be compiled. `git clone --depth 1 --branch 5.11.0 https://github.com/Audiveris/audiveris.git`, then `JAVA_HOME=<jdk-25> ./gradlew --no-daemon build` — **it declares source/target 25, so a JDK 21 fails with `invalid source release: 25`**; the build needs network only for its Maven deps (a warm `~/.gradle` cache makes it ~1 min, and it takes ~55 s otherwise). The launcher lands in `app/build/distributions/app-5.11.0.tar` → extract and run `bin/Audiveris`. `scripts/run_audiveris_omr.sh` does build-once/run-many.

```bash
TESSDATA_PREFIX=~/.config/AudiverisLtd/audiveris/tessdata \
  /home/ubuntu/.local/opt/audiveris-5.11.0/app-5.11.0/bin/Audiveris \
  -batch -force -save -export -output <proj>/work/omr -- <proj>/source/<score>.pdf
```

- Audiveris writes an `.omr` book plus one `.mxl` per input; ~5 min per 10–11-page choral score on 2 ARM cores. Put its own log in the project (`work/omr.log`), not in the terminal, because the interesting failures are per-sheet.
- Copy `eng.traineddata` into `~/.config/AudiverisLtd/audiveris/tessdata/` before the first run (`/usr/share/tesseract-ocr/5/tessdata/` or the tesseract-ocr/tessdata 4.1.0 raw URL).
- **Audiveris output is a cross-check, not a base:** it explodes a four-voice choral score into one `<part>` per detected voice with junk names lifted from the page (`"I:`, `3.`, `11.`), so part structure, staff grouping and printed labels must all be rebuilt even when the pitches are usable. Sanity-check an export by counting parts and measures before believing anything else about it.

## 7. Order of work

1. Classify the source; record staff-line geometry and the printed scale.
2. Validate OMR structure measure by measure (tuplets applied); repair short voices, drop spurious trailing measures.
3. Build the corrected MusicXML, force the printed system/page breaks, render to PDF.
4. Compare render against scan system by system — this is where octave shifts, displaced bar-line content, shifted syllables and dropped accidentals surface.
5. Fix, re-render, repeat; then package both editions with the uncertainty report.

Reading every bar out of crops before step 3 exists is the failure mode: coordinate bookkeeping eats the session and the deliverable slips. Keep the durable project tree (`source/ work/ out/ scripts/ report/`) and write each probe as a small re-runnable script under `scripts/`.

## 6. Which OMR engine to use as the draft

Julian supplies the raster draft himself and expects it to be the *base*; the scan stays the authority. Rank the engines accordingly:

1. **Julian's own captures** — the **MuseHub "Sheet Music Scanner" by Halbestunde** (a one-off paid desktop tool that only imports images/PDF and exports a scanned score as MusicXML/MIDI/PDF/**MSCZ**; it is *not* the Halbestunde freemium practice app and has no playback/loop/solo features — never describe it as such) and **Soundslice** (web; lyrics import but a stated risk of mixed-up instruments — verify every part/staff/clef assignment against the print). Use his file as the musical base and correct it; never silently re-derive it.
2. **Audiveris, self-built, as an independent cross-check only.** Build: `git clone --depth 1 --branch 5.11.0 https://github.com/Audiveris/audiveris.git`, then `JAVA_HOME=/usr/lib/jvm/java-25-openjdk-arm64 ./gradlew --no-daemon build` (5.11.0 needs **Java 25** — Java 21 fails with `invalid source release: 25`), unpack `app/build/distributions/app-5.11.0.tar`. Run: `TESSDATA_PREFIX=~/.config/AudiverisLtd/audiveris/tessdata <dir>/bin/Audiveris -batch -force -save -export -output <outdir> -- <pdf>`. On 2 ARM cores ≈5 min per 11-page score. Its output reliably splits the choir into meaningless parts (`Voice0…`, or OCR noise like `"I:`, `3.`) — useful for pitches/rhythms, not for structure.
3. **MuseScore NoteVision** (musescore.com, since July 2025; replaces the Audiveris the site ran for years). Web-only, no standalone app and no API: upload at `https://musescore.com/upload?format=PDF` (or Studio's File → Import PDF), it returns an editable **MSCZ** to download and refine locally. Claimed ≈95% recognition; free with an upload cap, unlimited on **Pro Plus**. Caveats to state to Julian: one-pass black box (no pre-export correction), and Muse Group says the feature *learns from uploaded files* — so licensed third-party scores are best uploaded only if that is acceptable; uploads are not auto-published and can be deleted, and the upload form's title/composer fields only matter if the score is published.

Where two engines disagree, the scan decides — do not average them or trust the newer one by default.

## 7. Choosing the base engine by measurement, not by vendor claim

Roles must stay separate: the **musical base** (structure, pitches, rhythm) vs. the **independent cross-check**. An engine only replaces another if a measured comparison says so. Agreed procedure for a new candidate (e.g. MuseScore NoteVision): take an already-finished, human-verified work, feed the *same* source PDF to the candidate, and compare its raw output against (a) our verified edition, (b) the engine currently used as base, (c) the cross-check engine — in that order: part/staff assignment and names, measure count and numbering, then pitches, rhythm and lyrics. Count the divergences; the fewest structural errors wins the base role. Never promote an engine on a ~95 % marketing figure.

Cost side of the same decision: Audiveris is local, free, unlimited, unattended and upload-free, which keeps it the natural cross-check; a web service with upload caps, one-pass output and a stated model-training use of uploads is an addition, not a like-for-like replacement.
