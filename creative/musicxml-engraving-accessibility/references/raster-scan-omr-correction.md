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

No fonts, no text, one large image per page → raster scan. The embedded image size (e.g. 1241×1755 for A4 at 150 dpi) is the detail ceiling: a crop rendered at 900 dpi holds the same information. **An OCR text layer does not make it a vector score.** A page carrying one large image *plus* a text layer set in a plain text font (Helvetica) is still a raster scan whose text layer is OCR garbage — a 300-dpi Whitacre scan returned `connissioned by the Moster Chorole of Tampo Bay` for `commissioned by the Master Chorale of Tampa Bay`. Use that layer only as a rough hint of where text sits; the image stays the authority. Decide vector vs. raster on *vector music drawings and music fonts*, never on the presence of extractable text. Record the embedded image size, and derive the printed scale from the staff lines (section 3) because that scale is needed later to reproduce the engraving.

## 2. Reading crops that are actually legible

- Threshold the overlay away: keep ink below ~150–170 grey, everything else white. Grey watermarks and page show-through vanish, the music stays.
- Keep each crop near the vision downscale limit (~1 MPix). Good shapes: 1–3 measures across the full system width at 400–500 dpi; a single staff only, at 800–1200 dpi, when pitch placement or ledger lines are in doubt.
- **The real limit of `vision_analyze` is the LONGEST SIDE (~1280–1300 px), not the pixel count**, and the same file can be loaded only ~3 times per session (region crops of one file count together). A 1100×1400 crop is silently halved and its noteheads stop being readable, while a 1100×1260 crop of the same content stays sharp. Size crops so `max(w,h) <= 1280` (e.g. all staves × 2 measures at 300 dpi); generate one file per reading instead of zooming repeatedly into a full page.
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

- **Every OMR engine drops the KEY SIGNATURE when spelling notes**: a note printed on the F line comes back as `F` (natural), not `F#`. Both Audiveris and Halbestunde did this, and their `fifths` values contradicted each other between parts (2/3/4/6 inside one file). Never trust the engine's key: count the sharps/flats from an enlarged key-signature crop and cross-check the count harmonically — a key is only right if every pitch class that actually occurs frequently is diatonic in it (frequent A natural AND frequent D# together force 4 sharps, not 3 or 5). Then decide for every engine-reported "natural" whether the printed key makes it a sharp/flat.

## 5. OMR engines — Audiveris, built and run locally

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

## 6. Order of work for a scan-plus-OMR job

1. Classify the source; record staff-line geometry and the printed scale.
2. Validate OMR structure measure by measure (tuplets applied); repair short voices, drop spurious trailing measures.
3. Build the corrected MusicXML, force the printed system/page breaks, render to PDF.
4. Compare render against scan system by system — this is where octave shifts, displaced bar-line content, shifted syllables and dropped accidentals surface.
5. Fix, re-render, repeat; then package both editions with the uncertainty report.

Reading every bar out of crops before step 3 exists is the failure mode: coordinate bookkeeping eats the session and the deliverable slips. Keep the durable project tree (`source/ work/ out/ scripts/ report/`) and write each probe as a small re-runnable script under `scripts/`.

## 7. Which engine is the base, which is the cross-check

Julian supplies the raster draft himself and expects it to be the *base*; the scan stays the authority. Rank the engines accordingly:

1. **Julian's own captures** — the **MuseHub "Sheet Music Scanner" by Halbestunde** (a one-off paid desktop tool that only imports images/PDF and exports a scanned score as MusicXML/MIDI/PDF/**MSCZ**; it is *not* the Halbestunde freemium practice app and has no playback/loop/solo features — never describe it as such) and **Soundslice** (web; lyrics import but a stated risk of mixed-up instruments — verify every part/staff/clef assignment against the print). Treat any draft he supplies (Halbestunde, Soundslice) as an **editable, discardable working file**: only the PDF he provides is the immutable original input and must be preserved unchanged. Use his file as the musical base and correct it; never silently re-derive it. Treat the export's *parts* as of unequal value: Halbestunde over-splits a choir **section-wise** when a voice drops out and re-enters (12 parts for a four-staff piece), so its note and staff data can be unusable while its **lyric time sequence** stays correct and worth reusing — count parts per measure before trusting its structure, and rebuild the staff layout from the print.
2. **Audiveris, self-built, as an independent cross-check only** — build and run commands are in §5. Its output reliably splits the choir into meaningless parts (`Voice0…`, or OCR noise like `"I:`, `3.`) — useful for pitches/rhythms, not for structure.
3. **MuseScore NoteVision** (musescore.com, since July 2025; replaces the Audiveris the site ran for years). Web-only, no standalone app and no API: upload at `https://musescore.com/upload?format=PDF` (or Studio's File → Import PDF), it returns an editable **MSCZ** to download and refine locally. Claimed ≈95% recognition; free with an upload cap, unlimited on **Pro Plus**. Caveats to state to Julian: one-pass black box (no pre-export correction), and Muse Group says the feature *learns from uploaded files* — so licensed third-party scores are best uploaded only if that is acceptable; uploads are not auto-published and can be deleted, and the upload form's title/composer fields only matter if the score is published.

Where two engines disagree, the scan decides — do not average them or trust the newer one by default.

Roles must stay separate: the **musical base** (structure, pitches, rhythm) vs. the **independent cross-check**. An engine only replaces another if a measured comparison says so. Agreed procedure for a new candidate (e.g. MuseScore NoteVision): take an already-finished, human-verified work, feed the *same* source PDF to the candidate, and compare its raw output against (a) our verified edition, (b) the engine currently used as base, (c) the cross-check engine — in that order: part/staff assignment and names, measure count and numbering, then pitches, rhythm and lyrics. Count the divergences; the fewest structural errors wins the base role. Never promote an engine on a ~95 % marketing figure.

Cost side of the same decision: Audiveris is local, free, unlimited, unattended and upload-free, which keeps it the natural cross-check; a web service with upload caps, one-pass output and a stated model-training use of uploads is an addition, not a like-for-like replacement.

**Measured result (Lobe den Herren, one already-verified work, all engines vs. the finished edition; notes compared as measure+pitch+duration multisets):**

| engine | notes | exact | missing | extra | recall | precision | lyric chars vs. corrected text |
|---|---|---|---|---|---|---|---|
| MuseScore NoteVision | 993 | 961 | 123 | 32 | 88.7 % | 96.8 % | 51.7 % |
| Halbestunde | 1095 | 957 | 127 | 138 (115 octave-only) | 88.3 % | 87.4 % | 68.0 % |

Both invented one extra final bar (75 instead of 74 measures) and both split into 4 staves, so structure is a wash. Note-level is a tie within noise — NoteVision's extras are scattered, Halbestunde's are one systematic octave block that is cheap to fix. Lyrics decide it: Halbestunde's errors are mechanical (missing umlauts, verse number glued to the first syllable) and its syllabic segmentation survives, while NoteVision's are word misreadings (`verstat`/`vereint`, `hommhechen`/`himmlischen`, `Glören`/`Chören`, `Pselter`/`Psalter`, `Herßs`/`Harfe`) plus stray punctuation. Verdict: NoteVision does **not** replace Halbestunde as the base; it is worth keeping as a third, engine-independent cross-check. Caveat: the reference edition descends from the Halbestunde base, which flatters Halbestunde's structure.

Practical defects seen: MuseScore 4.7.5 on this host **cannot open a NoteVision-produced MSCZ** (`-o out.musicxml file.mscz` exits 40, reproducible; adding a missing `automation.json` does not help) — parse the native `.mscx` inside the MSCZ directly instead. Audiveris 5.11.0 **crashed** on this score (`IndexOutOfBoundsException` during a page step, `Exit forced. Failure`) and produced no MusicXML, so "self-built OMR" is not a guaranteed column either.

**Write-protect the reference project during delegation.** When subagents are told to read a finished project as a pattern, one of them deleted `out/<name>-Master.mscz` from it. Instruct children to treat reference projects as read-only *and* verify those directories afterwards (compare against the project's own bundle/manifest) before trusting them as a baseline.

## 8. MuseScore 4.7.5 empty-staff hiding and the printed page count

Measured on Studio 4.7.5 headless (`xvfb-run -a musescore4 -o out.pdf in.mscz`), with `<hideEmptyStaves>1</hideEmptyStaves>` and `<dontHideStavesInFirstSystem>0</dontHideStavesInFirstSystem>` in `score_style.mss` (the `.mss` key keeps the old name; the binary also carries a `dontHideEmptyStavesInFirstSystem` symbol, but writing *that* spelling into the `.mss` changes nothing, and neither does injecting a `<Style>` block into the `.mscx`):

- **Hiding works per part, not per staff.** A one-staff part that has no notes anywhere in a system disappears (verified). A two-staff part whose *upper* staff is empty in every measure — with `<rest measure="yes"/>` **or** with genuinely note-less measures — still draws both staves. A 4-staff choir part therefore always draws four staves, even in a system where the print shows only the tenor/bass line.
- **The first system keeps its empty staves** even with `dontHideStavesInFirstSystem=0`; from the second system on they hide.
- **Practical consequences.** Reproducing a print whose staff count varies per system is impossible while the choir stays one part. Either split it into one part per voice (staff counts then match, but the source's part structure and shared „Chor“ label are lost — state that), or keep the part and shrink `<defaults><scaling>` until the printed *systems per page* fit again (for a 4-staff-choir-plus-piano score, 3.8 mm / 40 instead of the printed 5.08 mm / 40 was the largest value that still gave the print's 10 pages; 3.9 gave 11, 5.08 gave 12). Report the deviation instead of hiding it: the measure/system/page ranges can match the print exactly while the notation is smaller.
- **Verify pagination by text extraction, not by eye.** `for p in 1..N: pdftotext -f $p -l $p out.pdf -` and read the first measure number printed on each page; that maps page → measure range unambiguously. Tightening `staffDistance`/`minSystemDistance`/borders alone moved 12 → 11 pages and no further, which is the signal that the limit is the staff count, not the spacing.
- **The roundtrip comparison must ignore rests.** MuseScore materialises whole-measure rests for staves that are empty in a MusicXML measure, so an exported file has far more `<note>` elements than the source; key the comparison on (measure, staff, duration-in-quarters, pitch) for pitched notes only, plus a separate lyric multiset, or the gate reports thousands of bogus differences.
