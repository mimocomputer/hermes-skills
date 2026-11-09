# Realtime-Bruecke: Telefonkanal <-> KI-Sprachmodell (gemessen, Nov 2026)

Rezept, mit dem ein *Telefonat* bidirektional in Echtzeit an ein Sprachmodell geht —
ohne SIP-Trunk, ohne eingehende Firewall-Regel, ohne Fremdplattform im Medienpfad.

## Transportwahl zuerst klaeren (kostet sonst Tage)

- Die **Live-API** (`POST /v1/live/sessions`) akzeptierte fuer dieses Projekt nur `transport.type=webrtc`:
  `400 "Only the webrtc transport is supported."` — der SIP-Connector ist nicht freigeschaltet.
  Fuer „Anruf kommt von OpenAI hereingewaehlt“ haette man ohnehin eingehend TCP 5061 + SRTP
  in der Cloud-Sicherheitsliste gebraucht.
- Die **Realtime-API per WebSocket** funktioniert mit demselben API-Key sofort:
  `wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1` mit `Authorization: Bearer …`.
  Erste Antwort ist `session.created`, dann `session.update`. Nur ausgehende Verbindungen →
  keine Firewall-Aenderung, keine Zertifikate, kein SIP. Das ist der pragmatische Weg A.
- Modell- und Formatpruefung vorab: `session.update` mit `audio.input.format.rate=16000`
  wird abgelehnt („Expected a value >= 24000"); **24 kHz ist das Minimum** fuer PCM. Die
  Bridge muss also umrechnen (soxr `ResampleStream`, blockweise, kein Latenzaufbau).

## Asterisk-Seite: welche AudioSocket-Variante welche Rate liefert

| Weg | Rate | Beleg |
|---|---|---|
| App `AudioSocket(uuid,host:port)` | **8 kHz, fest** | `app_audiosocket.so` setzt hart `ast_format_slin`; gemessen 16 kB/s = 8 kHz |
| Kanal `Dial(AudioSocket/<host:port>/<uuid>/c(slin16))` | **16 kHz** | 640-Byte-Frames, gemessen 16,1 kHz; Gegenprobe `c(slin)` → 320 Byte / 8,1 kHz |

Der Kanal-Treiber ist die Wahl, wenn G.722 nicht am Socket verpuffen soll. Dial-String-Form
aus dem Quelltext (`channels/chan_audiosocket.c`): `AudioSocket/<destination>/<uuid>[/c(<codec>)]` —
`destination` ist `host:port`, die UUID ist Pflicht, das Format kommt aus `c(...)`.
`AUDIOSOCKET_UUID`/`AUDIOSOCKET_SERVICE` werden nur *gesetzt*, nicht gelesen.
Typische Fehler: `Destination '<uuid>' could not be parsed` (UUID an Stelle des host:port),
`UUID is required` (UUID fehlt), `Codec '<x>' not found`.

Protokoll: 1 Byte Typ + 2 Byte Laenge (big endian) + Nutzlast; `0x01` UUID, `0x10` Audio,
`0x03` DTMF, `0x00` Ende. **Achtung:** der Typ bleibt auch bei 16 kHz `0x10` — die Rate
ergibt sich ausschliesslich aus dem `c(...)`-Argument, nicht aus dem Typ-Byte.

### Richtungs-Asymmetrie des Paket-Moduls — geloest durch Eigenbau (Nov 2026)

**Loesung zuerst:** das Distro-Paket 22.5.2 (Build Aug 2025) ist aelter als der
Upstream-Commit `cb5b22db` (2025-10-10), der die breitbandigen Typcodes einbrachte. Baut man
`res/res_audiosocket.c` + `channels/chan_audiosocket.c` aus dem 22-Zweig gegen `asterisk-dev`
(Rezept in `references/audio-quality-and-codecs.md`), spricht der Kanal `0x12` in **beide**
Richtungen: 640-Byte-Frames je 20 ms (= 32 kB/s), G.722 172/172 Pakete ohne Verlust, vom
Nutzer als deutlich besser bestaetigt. Nach `apt upgrade` pruefen, ob das Paket die eigenen
Module ueberschrieben hat.

Das Folgende beschreibt weiterhin gueltig den Zustand *mit dem Paket-Modul*:

Upstream Asterisk 22 *kennt* breitbandige Typcodes (`0x12` = 16 kHz, `0x13` = 24 kHz) —
**das Paket-Modul tut das nicht**. Gemessen am Debian/Armbian-Paket 22.5.2:
`strings res_audiosocket.so` zeigt keine der `slin16`-Konstanten, und ein Frame mit `0x12`
wird verworfen (*"Received AudioSocket message other than hangup or audio"*). Ergebnis:

- **Asterisk → uns:** sendet bei `c(slin16)` 16-kHz-Daten, aber **mit Typ `0x10`** — die Rate
  muss man aus dem Dial-String kennen.
- **uns → Asterisk:** `0x10` wird hart als **8 kHz** gedeutet. 16-kHz-Nutzlast mit `0x10`
  = halbe Geschwindigkeit → **sehr tiefe, langsame Stimme**, und danach kam gar keine Antwort
  mehr. Konsequenz: Ausgang auf **8 kHz** rechnen (24 kHz Modell-PCM → soxr), 320-Byte-Frames
  (20 ms), Typ `0x10`. Verstaendlichkeit bleibt voll; der Dump bei 8 kHz transkribiert wortgleich.

**Beweis statt Vermutung — Ton-Test (2 Minuten):** 1-kHz-Sinus in 20-ms-Frames mit dem zu
pruefenden Typcode senden, auf der Asterisk-Seite aufnehmen, im Aufnahme-PCM die Frequenz
ueber Nulldurchgaenge messen. 1000 Hz = Rate stimmt, 500 Hz = halbe Rate. Messung hier:
1 kHz-Nutzlast als 8 kHz + Typ `0x10` → **1000 Hz / 7,0 s Aufnahme** (richtig).

## Transport B: UnicastRTP — als Breitbandweg VERWORFEN (nur noch Wire-Format-Referenz)

**Nicht verwenden.** Die Leserichtung ist in diesem Build defekt: mit einem gebrueckten
AudioSocket-Peer als Messinstrument kamen von 381 von Asterisk als empfangen geloggten
RTP-Paketen **0 Byte** in der Bruecke an (kein strict-RTP-Verwerfen, simple_bridge,
Translation vorhanden). Nur die Schreibrichtung funktioniert — deshalb bestehen lokale
Vorlesetests und echte Anrufe bleiben stumm. Messdetails:
`references/audio-quality-and-codecs.md`.

Der Abschnitt bleibt als Wire-Format-Nachschlagewerk stehen (Payload big endian, Pad-Bit
ignorieren, Taktrate ueber `comfort_silence`), falls ein spaeterer Asterisk-Build das
repariert.

Damals gedacht als Umweg um die 8-kHz-Grenze des Paket-Moduls, ohne selbst zu bauen:

```
[ai]
exten => s,1,Answer()
 same => n,Dial(UnicastRTP/127.0.0.1:9094/c(slin16)p(118),3600,d)
```

`chan_rtp` (Kanal-Treiber, im Debian-Paket vorhanden) versteht die Optionen `c(<codec>)`,
`p(<96-127>)` (dynamischer Payload-Typ fuer Senden UND Empfangen), `e(<engine>)`, `g`
(RTP-Glue) — Quelltext `channels/chan_rtp.c`, `AST_APP_OPTIONS(unicast_rtp_options …)`.

Gemessenes Wire-Format (der Teil, an dem man ohne Analyse scheitert):

- Jedes UDP-Paket **652 Byte** = 12 Byte RTP-Header + **640 Byte Nutzlast** (20 ms slin16
  @ 16 kHz), PT 118, Zeitstempel **+320** pro Paket.
- **Die Nutzlast ist big endian (L16, Netzwerk-Byte-Order).** Wie little endian gelesen
  klingt sie wie Rauschen (Schwerpunkt ~4 kHz, RMS ~17k, Nulldurchgaenge ~7000/s); als
  big endian gelesen transkribiert sie **wortgleich** (Schwerpunkt 1,4-2,7 kHz). Beim
  Senden ebenso zurueckwandeln (`np.frombuffer(frame,'<i2').astype('>i2')`), sonst hoert
  die Gegenseite Rauschen.
- **Das Padding-Bit (0x20) im zweiten Header-Byte wird ohne echte Fuellbytes gesetzt**
  (b1 = 0x76 = 118|0x20). Wer es „korrekt" auswertet (`payload[-1]` = Anzahl), verwirft
  pro Paket ~40 % der Nutzlast: unvollstaendige Saetze, Whisper-Halluzinationen.
  Pad-Bit ignorieren.
- **Asterisk sendet erst, wenn der Schenkel Audio hat** — im Testaufbau ohne `Playback`
  kommt gar kein RTP an (leere Aufnahme, keine Bridge-Verbindung): fuer Tests vorspielen.
- **Watchdog noetig:** ohne eingehendes RTP die Bruecke beenden (z. B. 10 s), sonst bleibt
  die WebSocket-Sitzung offen (Kosten) und die naechste Verbindung findet veralteten
  Zustand vor. `comfort_silence` (20-ms-Nullframes als stetiger Takt) darf nicht als
  Antwort-Audio gezaehlt oder in den Dump geschrieben werden.

Nutzen: 16 kHz in beide Richtungen — genau die Obergrenze, die die Fonjal-Strecke ohnehin
hat (G.722 = 16 kHz, Trunk kann kein Opus).

## Die stille Falle: ohne Stille antwortet die VAD nie

Asterisk liefert **keine Stille-Frames**, wenn der andere Schenkel nichts sendet. Wer nur
die empfangenen Frames weiterleitet, schickt nach dem Ende der Sprache nichts mehr — die
Server-VAD sieht dann nie `speech_stopped`, und es kommt **keine Antwort** (im Log: Audio
kommt an, `von KI: 0.0 s`, keine Transkripte). Fix: ein Feeder-Task haelt den Strom
lueckenlos bei 20 ms und fuellt Leerlauf mit Nullbytes. Danach kamen im Test
`speech_stopped` → `committed` → `response.created` → Transkript → Antwortaudio.

## Antwortrichtung

- `response.output_audio.delta` (aeltere Versionen: `response.audio.delta`) mit base64-PCM,
  zurueckrechnen auf die Kanalrate, in 20-ms-Haeppchen **getaktet** senden (der Server
  liefert schneller als Echtzeit; ohne Taktung laeuft der Puffer voll).
- **Kein Requeue von Frame-Resten.** `while len(buf) >= FRAME_BYTES` + anschliessendes
  `out_queue.put(buf)` fuer den Rest ist ein Leerlauf-Loop (`get` → zu kurz → `put` → `get` …):
  ~70 % CPU, Log steht still, der Verbindungsabbruch wird nie bemerkt. Reststueck in einer
  **lokalen** Variablen puffern. Zweite Absicherung: `writer.drain()` mit
  `asyncio.wait_for(..., 5)` — ein Peer, der nicht mehr liest, blockiert sonst ewig.
- Barge-in: bei `input_audio_buffer.speech_started` Warteschlange leeren und `response.cancel`
  **nur** senden, wenn eine Antwort laeuft — sonst kommt `response_cancel_not_active`.
- Ein `response.create` mit `instructions` direkt nach dem Verbindungsaufbau laesst die KI
  zuerst gruessen; ein Mensch am Telefon spricht sonst ins Leere.
- Der Angerufene hoert die KI nur, wenn der Bridge-Prozess waehrend des Anrufs laeuft:
  als `systemd --user`-Dienst (idle kostet nichts, die WS-Verbindung entsteht pro Anruf),
  Dialplan-Kontext z. B. `Answer()` + `Dial(AudioSocket/127.0.0.1:9092/${UUID()}/c(slin16),3600,d)`.

## Pruefen ohne Telefonat

`channel originate AudioSocket/127.0.0.1:9092/<uuid>/c(slin16) application Dial Local/s@<ctx>`
spannt den Socket-Kanal gegen einen Lokalkanal: der spielt eine Frage (`Playback`) und
zeichnet die Antwort auf (`Record`/`MixMonitor` schlaegt bei `.slin16` manchmal fehl —
zuverlaessiger: die Bridge schreibt das ausgehende PCM selbst per `--dump` mit).
Erwartete Beweiskette im Log: `Anrufer: <Frage als Transkript>` → `Agent: <Antwort>` →
Dumpdatei mit passender Laenge.

Fuer den RTP-Weg analog: `channel originate UnicastRTP/127.0.0.1:9094/c(slin16)p(118)
application Dial Local/s@<ctx>` — der Kontext muss etwas abspielen, sonst kommt kein RTP.
Byte-Order-Kontrolle: Nutzlast als big endian interpretieren und die 1-kHz-/Sprachprobe
mit Batch-STT verifizieren (little endian ⇒ Rauschen).

## Kosten (Okt 2026, nachgeprueft)

gpt-realtime-2.1: $32/1M Audio-Input, $64/1M Audio-Output → grob $0.02/min Zuhoeren,
$0.08/min Sprechen; mini-Variante $10/$20 (≈ $0.016/min). Audio-Token: 1 Token ≈ 100 ms
Eingang, ≈ 50 ms Ausgang.
