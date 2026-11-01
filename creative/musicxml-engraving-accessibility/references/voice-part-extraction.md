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
  voices) = genuine tacet = rests. The unison line can also live on the *other* staff of the
  part (measured: Christus Immanuel — the men's line occupies the **bass** staff for T. 9–21,
  so a tenor extract built from the tenor staff alone opens with 21 bars of whole-measure rests
  and the tenor's sung beginning is simply gone, while the split-off bass parts carry it).
  Always check each part's **first sounding measure** against the print.
* **Shared choral text.** One printed text line often hangs syllable-by-syllable on *different*
  voices of the same staff (measured in two works: the two voices of a T/B staff **never**
  shared a lyric onset). Adopt the sibling syllable at the **same onset**
  for notes of the target voice that carry none, but **never** while the target's previous
  syllable is still sounding (track `lyric_end = onset+duration` of the last lyric-bearing note
  and require `onset >= lyric_end`). Only for single-voice output
  parts: in a two-voice (divisi) part the voices would label each other.
* **Borrowing text across staves: the print decides, and exact onset+duration equality is the
  discriminator.** Where a system prints **one** lyric row for SA and TB (the shared-line case),
  the lower staff is wordless in the source, and refusing the cross-staff copy there ships a
  part with no words in whole sections. Copy the upper row onto the lower staff's sounding notes
  only where **onset AND notated duration are identical**; staggered (antiphonal) lower lines
  never match exactly on every note, so the test separates the two cases without judgement, and
  nothing is borrowed onto rests or under a different vowel passage. Verify two or three passages
  on the print; where the print's own second text row sits under the lower staff, that row wins.
  (An earlier note on this work called the two rows antiphonal — the re-measured print shows one
  shared row; trust the re-measured print over the older note.)
* **Divisi belongs to the singer-group level.** A staff that carries two real simultaneous voices (measured: Christus Immanuel bass, v13 20 notes + v14 214; Rutter *The Lord bless you*, m. 45 men in two voices) is a divisi of that section. Deliver the two lines as two addressable parts (Tenor 1 / Tenor 2 with the same music where they agree, per the user's convention) rather than as voice 1 / voice 2 of a single staff; if a finished delivery still carries a second voice (e.g. Rutter 09 m. 45), report it and offer the split, and do not lyric-borrow between them.
* **Rest-plus-note in one measure is an artefact, not a divisi.** Measured (Christmas Lullaby,
  m. 49/53): a whole-measure rest in voice 1 beside the sounding note in voice 2, in *both* the
  tenor and the bass file. The measure is not polyphonic — the note is the content. Normalise by
  putting the sounding line into voice 1 and dropping the phantom rest (it disappears anyway,
  because the note fills the measure), and name the measures in the report.

## Completing a part the source assigned to the wrong staff, or left wordless

Two defects that every standard gate below passes through:

* **Whose line is it?** A source can carry the men's line on the *bass* staff for a unison
  passage whose own label reads "TENOR und BAß unis.", so a split driven by staff/register hands
  the passage to the bass parts and gives the tenor nothing. Tie-breakers, cheapest first: (1)
  the printed labels — a system marked "T. B." at one staff means two voices on that staff; (2)
  the **independent OMR draft's** part structure: a line the OMR engine ends as its own part and
  that continues into the known melody of the next phrase is that singer, and that continuity
  across the phrase boundary is the decisive evidence; (3) register of the two lines where the
  source itself switches to two staff voices. Rebuild the extract from the file that actually
  carries the line — never hand-copy notes between extracts.
* **A part with no syllables at all.** The lyric checks (hunspell word audit, G12 hyphenation
  audit, note-text coverage) all test material that is *present*; a wordless staff passes every
  one of them. Run a **syllable census per staff and measure** (sounding notes vs. notes carrying
  a syllable, per row) and compare the wordless stretches against the print — that is the only
  check that finds missing text.
* **Document every completion in the report.** A filled passage is not a silent repair: name the
  measure range and the file it came from, and append it as a dated addendum to the existing
  report rather than rewriting it. Route corrections back through the extract builder so the
  addendum text is generated instead of typed by hand.

## Delivery form for an extract set

An extract set is a delivery like any other and gets the agreed form — per voice the native
`.mscz` **and** the `-DAISY.mxl` (`-DAISY` only on the MXL; the MXL must be packed from the
tagged MusicXML because MuseScore's own export drops `xml:lang`), plus the German report. An
`.xml`-only handover is a deviation; if one happened, name it and re-deliver, and keep the
uncompressed XML out of the share afterwards (project folder as the authoritative source).

* **Language tagging per lyric row:** `xml:lang` on `<text>` (delivery: `de` / `en`). Determine
  the language of **each row from its text**, never from the row position — measured: work 02
  prints row 1 in English and row 2 in German, 01 has four German strophes, others are
  German-first or single-language. Files whose source was already tagged keep their tags.
* **Editorial metadata per extract:** `<miscellaneous-field>` for `Stimmauszug`,
  `Quelle der Stimme`, `Bearbeitung`, plus `T/B split` on split-off parts and any correction
  note. The `<miscellaneous>` element may already exist — append the fields inside it.
* **Checks:** XSD on every tagged file; the MXL payload must be byte-identical to the tagged
  XML; MuseScore must open every `.mscz` and every `.mxl` (sample) and the `.mscz` roundtrip
  must reproduce the pitched and lyric multisets. Expect the language tags to be gone from
  MuseScore's own export and say that the MXL is the file for the braille translator.
* **Audit German lyrics only** once the rows are tagged: filter the syllable stream by
  `xml:lang="de"` before running hunspell, otherwise the English rows drown the report.
  Expect OMR letter damage in exactly this class (measured, work 03: `Fiihr`/`flihr` for
  “Führ”, `geniigt`, `fiir`, `sanfres`, `zZu`) — report it, do not silently “fix” the source's
  syllables.

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
   unison/divisi spots, syllable placement), plus the **first sounding measure of every part**
   and the syllable census per staff. This catches what the clock check cannot: a part that is
   clock-perfect and still empty where a unison line sat on the other staff, or a staff that
   carries no text at all.
5. Upload and compare `getcontentlength` against the local byte size for every file.
