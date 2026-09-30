---
name: musicxml-engraving-accessibility
description: Audit and fix MusicXML/MXL scores for DAISY accessibility.
version: 1.0.0
author: Hermes curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [musicxml, mxl, music-braille, daisy, accessibility, musescore, engraving]
    category: creative
    related_skills: [accessible-visual-verification, ocr-and-documents]
---

# MusicXML Engraving & Accessibility (DAISY Guidelines)

## When to Use
Use when checking, cleaning, fixing, or converting digital music notation scores (MusicXML / `.mxl` / MuseScore) for accessibility, especially compliance with the **DAISY Music Braille Engraving Guidelines** (for blind musicians, braille music translation, or screen reader usage). Also applies when comparing scanned/PDF master scores against digital MusicXML files to restore missing text, bilingual lyrics, or correct structural engraving flaws.

## Core Principles & DAISY Guidelines Checklist

The DAISY Engraving Guidelines ensure that MusicXML files are "born-accessible" and export reliably into Braille music (via Sao Mai, Braille Music Compiler, etc.) and Modified Stave Notation without silent data corruption.

### 1. Structure & Layout (DAISY G1, G10, M1–M3)
- **Score Metadata:** Ensure `<work>`, `<work-title>`, and `<creator>` (composer, lyricist, translator) are present in the XML header.
- **Part and Staff Labels:** Every staff/part must be correctly labelled (`<part-name>`, `<part-abbreviation>`) in the score's original language (e.g. "Sopran und Alt", "Klavier" / "S. A.", "Pno.").
- **Upbeat / Pickup Measures (Anacrusis):** An incomplete opening measure must be designated with `implicit="yes"` in `<measure>` so bar numbering matches the published print edition exactly. Never introduce fake full time signatures for pick-up bars.

### 2. Lyrics & Syllabic Structure (DAISY G12)
- **Lyric Text vs. Musical Directions:** Never place musical directions (tempo markings, dynamics, agogic instructions like `rit.`, `a tempo`, `Largamente`) into `<lyric>` tags. They must be encoded as `<direction>` with `<words>` or `<dynamics>`.
- **Syllabification:** Every syllable must have its `<syllabic>` element set properly (`begin`, `middle`, `end`, `single`). Missing or broken syllabic tags corrupt word grouping in braille music.
- **Hyphenation & Melismas:** Extended notes on a syllable must use `<extend />`. Notes sung on the same syllable across pitches (melismas) must be connected with `<slur>` to ensure the braille translator assigns the syllable to all constituent notes.
- **Multiple Languages / Strophes:** Distinguish verses and languages using the `number` attribute in `<lyric number="1">` (e.g. primary language / verse 1) and `<lyric number="2">` (e.g. secondary language / translation), rather than intermingling them in arbitrary voices.
- **Silent Voices:** Do not copy lyrics into accompanying staves or voices that do not actually sing words (e.g. homophonic choral accompaniments humming or singing neutral vowels).
- **Shared choir text:** A source can print shared words only below the upper choral staff. Include them in a lower singing part at confirmed matching syllable onsets, but never on its rests or during a different text/vowel passage. Normalize lyric row numbering across systems, because geometric extraction can shift Korean/phonetic rows when adjacent text appears.
- **Language schema:** Put `xml:lang` on the MusicXML lyric `<text>` element, not on `<lyric>`; the latter is rejected by the MusicXML 4.0 XSD. Validate against the official schema after adaptation.

### 3. Directions & Dynamics Placement (DAISY G2, G3, G13)
- **Hierarchy:** System text first, staff text second, dynamics last.
- **Keyboard / Grand Staff:** Hairpins or dynamics between two staves should be attached to the upper staff (unless completely resting) and positioned appropriately, avoiding hidden auxiliary notes or voices that trigger false collision warnings in braille transcribers.

### 4. Technical MXL/MusicXML Handling
- `.mxl` files are standard zip archives containing `META-INF/container.xml` pointing to the root `.xml` score (typically `score.xml`).
- To inspect or edit programmatically:
  ```python
  import zipfile
  with zipfile.ZipFile("score.mxl", "r") as z:
      z.extractall("extracted_score/")
  # Edit extracted_score/score.xml ...
  with zipfile.ZipFile("repacked.mxl", "w", compression=zipfile.ZIP_DEFLATED) as z:
      z.write("extracted_score/META-INF/container.xml", "META-INF/container.xml")
      z.write("extracted_score/score.xml", "score.xml")
  ```

## Pitfalls
- **Automated OMR / Scans:** Scores converted via optical music recognition (Scan-to-MusicXML) frequently dump expressive tempo text (like "poco rit." or "a tempo") directly into lyrics of nearby notes. Always audit `<lyric>` text content against a whitelist of musical direction terms.
- **Verify the actual MuseScore binary:** Run `mscore --version` / `musescore3 --version`; the `mscore` command can still be MuseScore 2 even when a newer version was expected. DAISY M2 calls for at least MuseScore 4.0.2. For requested latest v4, query official `musescore/MuseScore` GitHub release assets, choose host architecture, and verify the asset SHA-256 before execution.
- **Headless MuseScore execution:** Older versions often work with `QT_QPA_PLATFORM=offscreen`. Recent Studio AppImages may still select XCB despite that variable; use `xvfb-run -a /path/to/AppRun ...` and install `xauth` plus reported missing libraries. Extract an AppImage using `--appimage-extract` for FUSE-free server operation, keep the extracted directory with its launcher, and test an actual MusicXML-to-PDF and MSCZ conversion; `--version` alone does not verify rendering.
- **Repeat playback verification:** Do not trust MusicXML `<sound segno/dalsegno/tocoda/coda>` attributes to survive MuseScore import. Studio 4.7.5 can turn these into plain StaffText and drop repeat behavior. Inspect the native Marker/Jump objects, restore palette-equivalent objects if needed, and verify an actual MIDI export against the expected unfolded measure order. Native system markers need explicit `track=0`; if appended after a polyphonic measure, the reader can assign track 1 and ignore the segno for playback. Preserve a separate authoritative MusicXML when editor export drops language/editorial metadata.
- **Metric modulation:** MusicXML `sound/@tempo` is quarter-note BPM. At a printed dotted-quarter = quarter change, update the numeric tempo as well as encoding the visible modulation; ordinary text alone leaves playback at the previous quarter BPM.
- **Vector-PDF transcription:** Inspect music-font glyph coordinates and drawing paths before installing heavy OMR. Vector PDFs can retain noteheads, rests, staff lines, stems, beams and ties independently. Tesseract handles text, not reliable musical recognition. Check every measure's durations and compare rendered notes to source images; structural validity alone does not establish musical accuracy.
