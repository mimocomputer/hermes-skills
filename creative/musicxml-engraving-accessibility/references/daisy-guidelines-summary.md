# DAISY Music Braille Engraving Reference

Rule list from the **DAISY Engraving Guidelines for engravers and music-setters** (born-accessible
master scores) — verified against the published page on **2026-10-30**:

<https://daisy.org/activities/projects/music-braille/accessible-music-publishing/daisy-engraving-guidelines/>

**Page version: "Last updated: 10.06.2025 by the DAISY Consortium"** (10.06.2025 added to G1: "All
staves should be correctly labelled"). Lead author Haipeng Hu, DAISY Music Braille Project Technical
Consultant, with Dr. Sarah Morley Wilkins (Project Manager); feedback address `musicbraille@daisy.org`.
The guidelines are updated occasionally and new items are dated, so re-read the page before quoting
an ID — **numbering has shifted between versions** (see the last section). This file is a checklist;
it does not replace the page.

Scope of the published document: it applies (a) when creating a score from scratch, (b) when
correcting a scanned score, (c) when correcting an existing badly-engraved score; it addresses every
notation tool and every standard notation type. It never changes what a score looks like, only how it
is encoded, so that MusicXML export carries the structure braille, Modified Stave Notation, talking
scores and screen readers need.

**Read order prescribed by DAISY** (page wording: "Everyone should read the General Guidelines, plus the
specific Guidelines about the notation editor they're using"): all engravers read the General
Guidelines first, then the MuseScore or the Sibelius section.

## Key points before the numbered rules

- Use the latest version of the notation software and export **MusicXML**; for Sibelius use the most
  recent **Dolet** plugin (native export does not guarantee accessibility); for Finale open in the
  latest version (v27, sunset version) and export a compressed **MXL**.
- Use the software's palette/gallery elements (tempo, dynamics, lyric text, fingering …) so they
  export correctly.
- **Attach/anchor** every element (slurs, dynamics, lyrics) to the correct note or location — no
  floating objects, no dragging from a wrong place to a right one.

## General Guidelines (all engravers)

### 1. General

- **G1 — Reflect the layout of the original print score.** Keep pagination, bars per system, systems
  per page, instrument combinations. **All staves correctly labelled** (added 10.06.2025); instrument
  names and abbreviations in the original language, so blind musicians can talk to sighted teachers
  who read the print.
- **G2 — Position elements correctly.** All texts, marks, articulations and symbols at their correct
  position, in the correct voice, attached to the correct note/rest (text frame, plain text, system
  text, staff text, metronome text, footnote, lyrics, chord, symbol, articulation …). Do not drag an
  object from a wrong place to a right one (exceptions: G13, S14, S15).
- **G3 — Input text in correct order.** Enter the topmost staff text first, then lower ones: system
  texts first, then staff texts, then dynamics. Dragging does not change the exported order;
  re-enter instead.
- **G4 — Use default music and text fonts.** Special fonts only where a symbol really requires it.
- **G5 — Use standard symbols and lines.** Enter symbols/lines normally from the software; avoid heavy
  drawing, customisation or graphic import. Custom items get an "NB" text annotation so the braille
  transcriber knows what to do. Glissandos: standard glissando lines/slides, not other lines. Breath
  marks: the real breath mark, never a literary comma.
- **G6 — Position hairpins and lines accurately.** Put start and end of a hairpin at the precise
  locations and do not drag afterwards. For an ottava line (8va/8vb) first select all affected notes
  and then create the line, so every note is enclosed. Same for all other line objects.
- **G7 — Define glissando line position.** A glissando without a printed start and/or end note gets
  invisible grace note(s) for the missing end(s) — the original rest must not be occupied.
- **G8 — Avoid unnecessary hidden notes.** No hidden auxiliary playing notes, articulations, dynamics
  or pedals added for playback unless requested: MuseScore in particular exports them into MusicXML
  and they clutter the braille.
- **G9 — Copy and paste passages carefully.** Check every pasted passage against the print; similar
  passages are often slightly different.
- **G10 — Present special accidental rules carefully.** For scores with unusual accidental rules
  (accidentals valid only for the current notes, an accidental restated on a tied note but not on
  other same notes in the bar …) choose the matching accidental settings in the engraving rules, or
  apply the accidentals manually. Wrong settings still look normal but play and export wrong pitches.
- **G11 — Export "compressed MusicXML" (.mxl) if possible.** MXL can carry images and linked parts
  (e.g. Finale keeps special symbols as .svg, which can be represented in braille). Not possible in
  Sibelius, which exports uncompressed MusicXML through Dolet only.

### 2. Vocal

- **G12 — Present lyrics appropriately.** All lyrics correctly worded and hyphenated so braille
  software groups words correctly, and all notes slurred to match the lyric syllables so each
  syllable is associated with the correct note(s).

### 3. Keyboard

- **G13 — Insert markings between staves by dragging** (deliberate exception to G2). For keyboard or
  harp music, a dynamic, hairpin or text that belongs between two staves is entered on the **upper**
  staff and dragged down — unless the upper staff is completely empty (full-measure rest) in that
  measure.
- **G14 — Apply hand alternations in the same voice.** A cross-staff passage keeps the same voice
  throughout, so the passage lands in the correct braille staff and slurs export correctly.
- **G15 — Clean hidden rests.** In keyboard music with partial voices or a staff reserved for hand
  alternation, remove the filler rests after input (in Sibelius: delete the remaining-beat rest
  twice).
- **G16 — Mark accidentals in different parts appropriately.** With several voices on the same note
  where only one has a non-key accidental, check whether the same notes in the other voices play
  correctly; a note crossed from another staff **must** carry its own accidental (it does not share
  the other staff's accidental).

### 4. Ensemble

- **G17 — Handle combined instrument staves carefully.** Do not split a staff holding combined
  instruments (including string divisi) into several staves, and do not merge separate staves of the
  same instrument type — unless the transcriber or end user requests it. If splitting/merging is
  requested, every individual staff carries all necessary information (articulations, slurs,
  dynamics, texts), or the combined staff avoids duplicated elements (unless the combination is
  written as multiple voices rather than chords).
- **G18 — Avoid instrument changes.** For scores with many instrument changes/combinations keep each
  combination as one staff with the correct name/abbreviation and hide unused staves. (MuseScore
  engravers may instead use MuseScore's instrument changes — see M1/M20.)
- **G19 — Present shared markings on each staff.** A dynamic, hairpin or text that applies to a group
  of staves (e.g. "pizz." and "sff" between two divisi staves of violin I) is entered on **both**
  staves; braille needs it on both. Common in early/mid-20th-century scores.

## MuseScore Guidelines

### 1. General

- **M1 — Use MuseScore properly.** All General Guidelines apply **except G18**; read the MuseScore
  handbook and support pages first.
- **M2 — Use the latest version of MuseScore** (at least V4.0.2) for notation and MusicXML export.
- **M3 — Use MuseScore palettes** for most symbols and lines; the "Advanced" workspace covers more.
  Only fall back to the Z "Symbols" list when the palette has nothing — those objects export poorly.
  Custom palettes are untested; avoid.
- **M4 — Combine text with dynamics.** "sempre f", "p cresc." etc. become **one** dynamic text object
  (enter the dynamic, then add the text in edit mode) so braille gets one string.
- **M5 — Use the Articulations palette for "Laissez Vibrer".** The palette l.v. applies one curve per
  note/chord and exports as a let-ring tie on every chord note; never fake it with a hidden note or
  chord.
- **M6 — Position a hairpin around notes with a new voice and hidden rests.** If a hairpin starts or
  ends between note onsets, do not drag it: use a new voice with hidden rests at the precise position.
  (A normal mid-measure note onset does not by itself need an auxiliary voice.)
- **M7 — Add an accidental to a trill line in the right order:** select the trill line first, then add
  the accidental, so both export as one standard trill-with-accidental.
- **M8 — Two trill marks in one chord:** input the first normally and the second as a symbol, until
  MuseScore supports both natively.
- **M9 — Use individual articulations for multiple articulations on one note** (e.g. tenuto + accent),
  not the composite palette item. Exception: the "loure" (tenuto-staccato) exports correctly as
  detache/portato.
- **M10 — Unmeasured cadenzas:** follow the MuseScore handbook's "Bar Operation" section to alter
  measure lengths and add uncounted measures.
- **M11 — No fake slurs or notes in cross-voice ties.** MuseScore connects ties between voices in the
  same staff automatically.
- **M12 — No hidden notes or voices in cross-staff ties.** First cross the notes to the other staff,
  then add the tie, then cross back; MuseScore connects notes on the same staff regardless of voice.
- **M13 — Notate fingerings correctly:** select each note of a chord and enter the fingerings that
  belong to it.

### 2. Keyboard

- **M14 — Use individual ottava lines for cross-staff chords.** Replace a long customised ottava line
  (as in the attached `ottava.mscz`) with individual lines that apply only to the crossed chords.
- **M15 — Follow the guidance for inputting figured bass** (attached `bsgbass.mscz`, an encyclopedia
  of figured bass).

### 3. Ensemble

- **M16 — Use the "Atonal" (open) key signature for contemporary ensemble scores** without key
  signatures, so transposed instruments do not show unwanted key signatures.
- **M17 — Use "Staff/Part Properties" for transposed-instrument key signatures** the palette cannot
  produce (e.g. Bb clarinets in Gb instead of F# major): set "preferred sharps or flats for transposed
  key signatures" to flats. If the opposite behaviour is needed, use a hidden instrument change to the
  same instrument with a different accidental preference, keeping name and abbreviation identical.
- **M18 — Input multiple time signatures separately** (ctrl+click to enter per staff). A known
  MuseScore bug can report a bar-length problem on reopening; delete the passage and re-enter the time
  signatures in a different order (see M19).
- **M19 — Workaround for local time signatures** if M18 still errors or corrupts the file: one main
  time signature, plus a displayed time signature in the "time signature" property text fields on the
  other staves and hidden tuplets to scale those notes.
- **M20 — Two ways to handle complicated instrument combinations and changes:** follow G17/G18, or use
  MuseScore instrument changes (including changing to the same instrument) to give different part
  names/abbreviations — this saves staves and resources in big scores.

## Sibelius Guidelines (compressed; the working tool here is MuseScore)

- **S1** follow the General Guidelines plus the Sibelius Reference Guide/Tutorial.
- **S2** latest Sibelius with the latest Dolet plugin (2023.x + Dolet 8 or later recommended).
- **S3** run the "There It Is!" plugin (Sight-Impaired category) with "Trace to log file only" for the
  whole score and hand the log to the transcriber; for orchestral scores with instrument changes or
  renamed staves also run "Trace Instrument Changes" (Developers' Tools).
- **S4** switch Sibelius to English so exported symbol/line names are correct.
- **S5** with English keyboard layouts, use Sibelius' built-in accent letters from the text-entry
  context menu.
- **S6** do not input symbols as Opus text characters (they export as letters); use the palettes.
- **S7** combined text + dynamic as **one** expression text (counterpart of M4).
- **S8** chord fingerings note by note, never as one multi-line fingering text.
- **S9** ornaments with accidentals: take the accidental from the Symbols gallery; no composite
  ornament, no text accidentals.
- **S10** give custom symbols/lines correct English names in the creation dialog so Dolet exports them
  by name.
- **S11** select notes inside an ottava line with the keyboard, so the line's end covers the last note.
- **S12** unmeasured cadenzas: real irregular bars (not fake time signatures) with correct accidentals;
  exception on measure numbering for continuation bars.
- **S13** special time signatures (2/4+3/4, 2/4=12/16): hidden real time signature plus the printed one
  as text, because Sibelius exports them wrongly from the time property (3+2+3/8 works normally).
- **S14** ottava workaround for hand alternations (attached `ottava.sib`, bar 2).
- **S15** in cross-staff passages attach extra accidentals and pedals to the correct notes with
  keyboard selection (looks slightly different from print, but is the only correct braille route).
- **S16** turn on "Transposing scores" for transposed instruments notated at written pitch.
- **S17** create unusual transposing instruments via "Edit Instruments" with correct properties.
- **S18** "Atonal" key signature for contemporary ensemble scores (counterpart of M16).

## Downloads shipped with the guidelines

Examples folder: <https://dl.daisy.org/projects/musicbraille/DAISY_Guidance_for_Engravers_Examples.zip>
(`ottava.mscz` for M14, `bsgbass.mscz` for M15, `ottava.sib` for S14).

## Related DAISY documents (check them when a task touches their topic)

- **Metadata Guidelines for Braille Music Scores and Music Books** (final 19.02.2023,
  <https://dl.daisy.org/projects/musicbraille/daisy-mus-brl-metadata-guidelines-finalized-feb-19-2023.pdf>):
  **core (C) elements** C1 Local Identifier, C2 Title Information, C3 Author or Composer,
  C4 Contributor, C5 Music Braille Format, C6 Music Braille Designation, **C7 Language** ("Record the
  language of any sung or spoken text within a score, such as song lyrics"), C8 Standard Identifiers,
  C9 Publisher Information, C10 Production Information, C11 Medium of Performance, C12 File Format
  (its example row names "Portable Embosser Format (PEF), Music XML, or MNX, etc."), C13 Extent.
  The **recommended** list continues with C14 Type of Braille Encoding, C15 Line length and page length
  and R1–R9 (Contents … Accompanying Matter). This is the published basis for tagging the language of
  lyric rows in the MusicXML master; the document is a *catalogue record* guideline, so it belongs in
  the report, not in the engraving rules.
- **eBraille 1.0** (specification published August 2025 — <https://daisy.org/s/ebraille/1.0/FINAL-ebraille-20250814/>
  — approved by the DAISY Board in November 2025; project page <https://daisy.org/activities/standards/ebraille/>):
  the modern digital braille format (EPUB 3-based, for refreshable displays, tactile graphics, reflowable
  braille). **Music braille is not yet covered** — the eBraille project update
  (<https://daisy.org/news-events/articles/ebraille-project-update/>) lists "Review the specialist and
  complex formatting requirements of Music Braille" among the work planned for the coming year, and the
  working group is still discussing music metadata. Do not claim eBraille delivery or music-braille
  support in eBraille.
- **DAISY proposal for MusicXML 3.2 and MNX** (11.03.2019,
  <https://dl.daisy.org/projects/musicbraille/DAISY_Proposal_for_MusicXML_3.2_and_MNX_for_w3c_11.03.2019.docx>):
  the requirements DAISY submitted to W3C — background for why a MusicXML master must carry structure
  instead of visual offsets.
- **Music Braille Production Network** (guidance for productions for international readership,
  04.07.2023) and the project overview <https://daisy.org/activities/projects/music-braille/>.
- Converter tools (name them in the report's "not tested" section). DAISY's project page names the two it
  supported directly: **MakeBraille** (MakeBraille-Hodder, from dzb lesen, Leipzig — online professional
  tool converting scanned print scores and MusicXML into music braille, licence-based) and **Sao Mai
  Braille (SMB)** (interactive tool for blind musicians). Also in use: **BrailleMUSE** (web transcription
  server), **GoodFEEL** (Dancing Dots). All are third-party; naming them is not an endorsement and none of
  them was run for a delivery unless the report says so.
- Superseded engraver documents are listed on
  <https://daisy.org/activities/projects/music-braille/latest-developments/>: 12 March 2021 (docx),
  16 February 2022, 1 April 2022, 8 July 2022 (zip) and the FINAL 30.03.2023 zip — all with example files.
  The current web page is the successor of that series ("Tips For Engravers To Produce Braille
  Transcription-Friendly Scores", 12.03.2021, Haipeng Hu). **Their numbering differs**, verified against
  the 12 March 2021 document: it ran General G1–G16, MuseScore M1–M17, Sibelius S1–S15, while the page now
  runs G1–G19, M1–M20, S1–S18. Examples of the shift — 2021 G2 = today's G17 (combined staves), 2021
  G5 = today's G12 (lyrics), 2021 G9 = today's G13 (markings between staves), 2021 M4 = today's M5
  (laissez vibrer), 2021 M5 = today's M6 (hairpin via a new voice), 2021 M15/M16 = today's M11/M12
  (cross-voice / cross-staff ties), 2021 M17 = today's M20, 2021 S9 = today's S14 (ottava workaround,
  `ottava.sib` bar 2), 2021 S15 = today's S13 (special time signatures). Always quote IDs from the page
  as re-read, never from an old download, and translate an ID you only know from an old copy.

## Workspace rules (this profile's additions, not DAISY rules)

- `xml:lang` on every lyric `<text>` (never on `<lyric>`, which the MusicXML 4.0 XSD rejects) records
  the language of the sung text (C7 above). It is a house convention for this delivery, justified by
  the metadata guidelines, not an engraving guideline.
- A voice split requested by the user is the **G17 exception**: all articulations, slurs, dynamics and
  texts must be present in every new staff, and markings that apply to a group go on all affected
  staves (G19). The split ships under its own name and folder, never under the transcription's name.
