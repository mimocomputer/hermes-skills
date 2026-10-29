# Extracting a single voice (Tenor/Bass/…) from a choral MusicXML/MXL

Use when a source score must be reduced to one singer's line as a standalone part.
The task is *not* a file filter: MuseScore voices are engraving voices, not singer parts.

## Order of work

1. **Map the layout first, per work.** Dump, per part, which *staff* and *voice* holds content
   and in which measures (run-length list of "voices present per measure"). The nine works of
   one delivery showed five different layouts: separate SATB parts; 2-staff `Chor` (SA/TB);
   4-staff `Chor` SATB; a 1-staff `Tenor und Bass`; and one score where the men's line moves
   between staves (unison strophe on the upper staff, second voice later, own staff at the end).
   **Never assume "staff 2 = TB" or "voice 1 = Tenor".**
2. **Never identify a voice by index alone — check the clef and the range.** A tenor staff can be
   treble-8, plain treble, or bass clef depending on the edition; keep the source clef
   (including `clef-octave-change`), do not "normalise" it.
3. **Rebuild the measure as a timeline, not as an element copy.** Walk each measure with a
   cursor (`note` advances, `<chord>` does not, grace does not, `backup`/`forward` move it),
   collect events per voice with onsets, then re-emit each target voice from tick 0 to the
   measure length with rests (`rests_for`, greedy standard-dot values) filling every gap.
   Measure length = max end over *all* voices of the measure, and `implicit="yes"` pickups
   stay shorter than the nominal meter.

## Three traps that make a naive split wrong

* **Unison inheritance.** Where a voice is empty but a sibling voice on the *same staff*
  sounds, both singer parts read the same printed line. Measured (Blick auf den Tag): the T/B
  staff is voice 5 only for T. 39–62 (print says "TENOR und BASS, unis."), so a plain voice-6
  extraction leaves the bass silent for 24 bars. Rule: if the target voice has no pitched note
  in the measure and a same-staff sibling has, take the sibling's line. Empty *staff* (all
  voices) = genuine tacet = rests.
* **Shared choral text.** One printed text line often hangs syllable-by-syllable on *different*
  voices of the same staff (measured in two works: the two voices of a T/B staff **never**
  shared a lyric onset). Adopt the sibling syllable at the **same onset**
  for notes of the target voice that carry none, **but never** (a) across staves — that imports
  the S/A text into a T/B part (Sternen-Carol's two rows are antiphonal, not shared) — and
  (b) while the target's previous syllable is still sounding (track `lyric_end = onset+duration`
  of the last lyric-bearing note and require `onset >= lyric_end`). Only for single-voice output
  parts: in a two-voice (divisi) part the voices would label each other.
* **Divisi belongs to the singer-group level.** A staff that carries two real simultaneous voices (measured: Christus Immanuel bass, v13 20 notes + v14 214; Rutter *The Lord bless you*, m. 45 men in two voices) is a divisi of that section. Deliver the two lines as two addressable parts (Tenor 1 / Tenor 2 with the same music where they agree, per the user's convention) rather than as voice 1 / voice 2 of a single staff; if a finished delivery still carries a second voice (e.g. Rutter 09 m. 45), report it and offer the split, and do not lyric-borrow between them.
* **Rest-plus-note in one measure is an artefact, not a divisi.** Measured (Christmas Lullaby,
  m. 49/53): a whole-measure rest in voice 1 beside the sounding note in voice 2, in *both* the
  tenor and the bass file. The measure is not polyphonic — the note is the content. Normalise by
  putting the sounding line into voice 1 and dropping the phantom rest (it disappears anyway,
  because the note fills the measure), and name the measures in the report.

## Splitting an already-delivered divisi part into one-voice files (dated follow-up pass)

Julian asked for this on 2026-10-29 and restated it as a standing convention: it is **not** a
default for transcriptions — only when he asks for it (in the brief or afterwards). Run it as
its own dated pass on the existing delivery, not as a silent rewrite:

* Per measure: a source measure with **one** pitched voice goes identically into **both**
  outputs (where the parts agree, both lines carry the same music — his rule); a measure with
  **two** pitched voices (real divisi) sends voice 1 to the `-1` file and voice 2 to the `-2`
  file. Force `<voice>1</voice>` everywhere, keep the barline, give each new part unique
  `xs:ID`s after deepcopy.
* Names: `…-Tenor-1.xml` / `…-Tenor-2.xml`, `…-Bass-1.xml` / `…-Bass-2.xml`; files that stay
  single-voice keep their old names, and every file that is *not* part of the split stays
  byte-identical. Move the superseded files into `deliver/archiv-<date>/` instead of deleting
  them, and delete the superseded names on the share **only after** the new names' remote sizes
  match the local byte sizes.
* Gates for the pass: XSD; per-measure clock; "exactly one voice per measure" asserted on every
  new file; a **per-measure content comparison against the pre-delivery file** (single-voice
  measure = identical in both outputs, divisi measure = matches the corresponding source voice);
  a full MuseScore roundtrip per new file (pitched multiset + lyrics); and a visual check of the
  split measures in the render.
* Expect the split second part to be **wordless** where the print hangs the text on the first
  voice: say so explicitly (with the affected measures) and offer the sibling-syllable rule from
  the extraction, instead of silently adding syllables or leaving the reader guessing.

## What to carry over, what to drop

* Keep: notes with `pitch/duration/type/dot/accidental/time-modification/stem/beam/notations
  (slur/tie/tuplet/articulations)/lyric`, `attributes` (divisions, key, time, transposition and
  the target staff's clefs, renumbered to staff 1, `staves` removed), `<barline>` (repeats,
  segno/coda), `<sound>`, work/movement-title, identification, defaults.
* Keep directions when `staff` is absent or is the target staff; additionally keep
  dynamics/wedge/rehearsal/metronome/pedal from *any* staff of the same source part (a part's
  rehearsal letters usually sit on staff 1 and would otherwise be lost). Drop `<staff>` from the
  copied direction and re-sort children (MusicXML child order is fixed).
* Drop: other parts/staves, `<print>` new-system/new-page (full-score layout), harmony,
  figured-bass, credits.
* **Sort `<identification>` and drop invalid children:** two supplied sources failed the
  official 4.0 XSD — 04 had `creator` after `encoding`/`miscellaneous` (order is creator*,
  rights*, encoding?, source?, relation*, miscellaneous*), 05 had an empty
  `<metronome><beat-unit/></metronome>`. Normalise in the output and report the source defect;
  do not silently ship a file that fails the schema.

## Verification gates (all cheap, all mandatory)

1. XSD-validate every output **and** the sources (the sources can be the broken ones).
2. Per-voice clock per measure against the meter, allowing `implicit` pickups to be short.
3. MusicXML → MuseScore 4 → MusicXML roundtrip; compare the **pitched multiset per
   (measure ordinal, staff, step/alter/octave, duration-in-quarters)** and the lyrics per
   (measure, verse number, text, syllabic). Compare durations as fractions of `divisions` —
   MuseScore re-exports with a different `divisions` and raw durations then look "wrong".
   Expect verse numbers to be renumbered on the roundtrip when the part uses non-contiguous
   verses (e.g. 1 and 4) — that is a MuseScore import artefact, not an extraction error.
4. Render 4–6 of the parts to PDF and read them against the print (noteheads, accidentals,
   unison/divisi spots, syllable placement). This catches what the clock check cannot.
5. Upload and compare `getcontentlength` against the local byte size for every file.
