# DAISY Music Braille Engraving Reference

Summary of essential rules from the DAISY Music Braille project guidelines (`daisy.org/activities/projects/music-braille/accessible-music-publishing/daisy-engraving-guidelines/`):

### General Guidelines
- **G1 (Original Layout & Staves):** Match pagination, system breaks, and measure numbering of the print edition. Keep staves correctly labelled in original language.
- **G2 (Element Positioning):** Anchor markings (dynamics, articulations, lyrics) to the correct note/voice rather than visual manual offset dragging.
- **G3 (Text Hierarchy):** System texts first, staff texts second, dynamics last.
- **G8 (No Hidden Playback Artifacts):** Avoid hidden notes/dynamics meant only for MIDI playback; braille transcribers interpret them literally.
- **G11 (Compressed MusicXML):** Prefer `.mxl` to retain packaging and linked assets.
- **G12 (Lyrics & Vocal):** Correct word spelling, hyphenation, `<syllabic>` markup (`begin`/`middle`/`end`/`single`), and `<slur>` connections for melismas.
- **G13–G16 (Keyboard Notation):** Inter-staff dynamics belong anchored to the upper staff; hand alternations stay in the same voice; clean redundant hidden rests; verify accidentals on cross-staff notes.

### MuseScore Specifics
- **M4 (Dynamics + Text):** Combine expressions like "sempre f" into a single dynamic text object so Braille transcribes a single token.
- **M5 (Laissez Vibrer):** Use the articulation palette's l.v. symbol, not fake tied chords.
- **M6 (Hairpin Positioning):** If hairpins start mid-measure, use a new voice with hidden rests rather than loose graphical dragging.
- **M11–M12 (Cross-Voice / Cross-Staff Ties):** Use native tie bindings without artificial duplicate notes or fake slurs.
