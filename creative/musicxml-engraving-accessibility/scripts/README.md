# Wiederverwendbare Pipeline: OMR-Vorlage → korrigierte Ausgabe

Diese Skripte sind aus der Korrektur von „Lobe den Herren" (Rutter) hervorgegangen und
sind werk-unabhängig. Projektform:

```
<projekt>/
  source/     Quell-PDF + OMR-Rohdatei
  work/       Zwischenstände (Renders, Crops, Parser-Ausgaben)
  out/        Fertige Dateien + bundle/
  report/     BERICHT.md
  scripts/    Kopie dieser Skripte + score_spec.py (werkspezifisch!)
  .venv       uv venv mit pymupdf lxml mido numpy scipy pillow
```

## Ablauf

1. `python scripts/render_pages.py` / `cleancrop.py` — Seiten rendern und sauber
   beschneiden (Schwellwert entfernt graue Wasserzeichen; 0 = schwarz).
2. `analyse_page.py`, `rowprobe2.py`, `barlines2.py` — System-/Notenzeilenlagen und
   Taktstriche im Raster bestimmen.
3. `heads4.py <page> <top> <bottom> <clef> <x0> <x1>` — Notenköpfe per Erosion +
   Komponentenanalyse finden und als Tonnamen ausgeben. Damit **objektiv** prüfen,
   wo ein OMR-Ergebnis eine Oktave daneben liegt (häufigster systematischer Fehler).
4. `mscx_read.py` — OMR-MSCX in ein Modell lesen: Systeme, Stimmen, Onsets, Dauern,
   Triolen, `tpc`-Vorzeichen, Silben.
5. `check_mscx.py` — Taktdauern je Stimme gegen das Metrum prüfen; kurze Innenstimmen
   und erfundene Schlusstakte finden.
6. `score_spec.py` (werkspezifisch, siehe unten) + `build_musicxml.py` — MusicXML bauen.
7. `pipeline.sh <Name>` — MusicXML → MSCZ → Style-Patch (`patch_mscz.py`) → PDF/MIDI/MXL.
8. `validate.py` — Taktuhr + XSD (`work/musicxml.xsd`, dazu `xml.xsd` und `xlink.xsd`
   lokal ablegen und die `schemaLocation` auf die Dateinamen patchen).
9. `roundtrip.py`, `roundtrip_pitches.py` — MusicXML → MuseScore → MusicXML vergleichen
   (Noten, Dauern, Tonhöhen, Silben). `check_midi.py` — Länge, Tempo, Repeats.
10. `lyric_audit.py` — gesungene Wörter aus den Silben rekonstruieren und gegen
    `hunspell -d de_DE` prüfen (findet fehlende Umlaute und Buchstabendreher); zusätzlich
    `hyphenation_faults()`: offene `begin`/`middle`-Silben, die nie von einem `end`
    geschlossen werden (Silbe fälschlich `single` oder Wort am Stimmenende offen) —
    bricht die Wortgruppierung im Braille (DAISY G12). Exit 1 bei Treffern, damit der
    Lauf in einer Kette auffällt. Beispiel: 07 Christmas Lullaby vor der Korrektur
    `"A`(T28)→`ve`(T29), `nei`(T46)→`ther`(T46), `"A`(T64)→`ve`(T65); danach 0.
11. `compare.py` — Scan-Ausschnitt über Render-Ausschnitt legen und visuell vergleichen;
    `bundle.sh` — Bundle + SHA-256-Manifest.

## score_spec.py — werkspezifische Angaben (Vorlage)

```python
TITLE = 'Lobe den Herren'
CREATORS = [('composer', 'Stralsund Gesangbuch 1665'), ('arranger', 'John Rutter')]
N_MEASURES = 74                     # Taktzahl des Drucks (erfundene OMR-Takte abschneiden)
LYOUT = [('P1', 1, 1), ('P1', 2, 4), ('P2', 1, 2), ('P2', 2, 3)]
                                    # (Part, Ausgabe-System, Quell-System)
PART_NAME = {'P1': ('Chor', 'Chor'), 'P2': ('Orgel', 'Org.')}
NEW_SYSTEM = {6, 12, 19, 26, 33, 40, 47, 54, 61, 68}   # gedruckte Systemumbrüche
NEW_PAGE = {26, 54}
VERSE_RANGES = [(12, 32, 1), (33, 53, 2), (54, 74, 4)]  # (von, bis, Strophe)
LABELS = [(1, 'P2', 1, 'Tpts.'), (3, 'P2', 1, 'Org.'), ...]
DYNAMICS = [(1, 'P2', 1, 'f'), ...]
TEMPO = ('Maestoso con moto', 96, 'quarter')
LYRIC_FIX = {('Ko', 15): 'Kö', ...}   # Silbe je Takt → korrigierter Text
PITCH_FIX = [(1, 26, 53, -12)]        # (Quell-System, von, bis, Halbtöne)
REPEAT = (33, 53)                     # Start-/Endtakt der gedruckten Wiederholung
```

## Was bei diesem Werk schiefging (Wiederholungsgefahr)

* OMR-Werkzeuge (hier: Halbestunde über MuseHub, Export über MuseScore 2) verlieren
  Triolen und schreiben b-Töne als Kreuz → `tpc` auswerten, nicht `pitch % 12`.
* Taktlängen verdoppeln sich, wenn beim MusicXML-Bau das `<backup>` zwischen den
  Systemen eines Parts fehlt.
* Systematische Oktavfehler: mit `heads4.py` gegenmessen, nicht raten.
* Liedtexte immer mit `lyric_audit.py` prüfen — der Audit fand in diesem Werk
  13 Textfehler, die beim Lesen „plausibel" aussahen.
