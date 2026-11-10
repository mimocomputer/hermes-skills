# Betriebs-Runbook: die laufende Telefon-Anlage auf diesem Host

Fuer jede Session gedacht, die einen *bereits aufgebauten* Stack bedienen, pruefen oder
anpassen soll — statt ihn neu zu planen. Alle Pfade relativ zu `$HERMES_HOME` (`~/.hermes`).
Zahlen/Nummern sind hier bewusst maskiert; echte Werte stehen nur in den `0600`-Dateien.

## 1. Inventar (was laeuft wo)

- **Asterisk 22.5.2** aus dem Distro-Paket (`asterisk`, `asterisk-modules`, `asterisk-dev`),
  Dienst `asterisk.service`, CLI `sudo asterisk -rx "<Befehl>"`.
- **PJSIP-Endpunkt `fo-endpoint`** registriert sich beim Anbieter (Trunk, UDP/5060).
  Pruefen: `sudo asterisk -rx "pjsip show registrations"` → muss `Registered` zeigen.
- **Brueckendienst `hermes-realtime-bridge`** (systemd *user*): `realtime_bridge.py`
  verbindet den Asterisk-AudioSocket-Kanal mit der OpenAI-Realtime-API.
  - Unit: `~/.config/systemd/user/hermes-realtime-bridge.service`
  - Code: `$HERMES_HOME/scripts/realtime_bridge.py` (live, massgeblich)
  - Konfiguration/Persona: `$HERMES_HOME/rt-bridge.env` (wird per `EnvironmentFile` gelesen)
  - Dumps: `/tmp/hermes_call/ai_reply.sln` (KI) und `ai_input.sln` (Anrufer), 16 kHz PCM
- **Zugangsdaten** (nie ausgeben, nie in den Chat): `$HERMES_HOME/sip.env` (SIP),
  `$HERMES_HOME/sip-targets.env` (`name=+E.164`-Ziele: `handy`, `backsim`, `fonial`),
  API-Schluessel in `$HERMES_HOME/.env`.
- **Dialplan-Generator:** `$HERMES_HOME/asterisk/gen_configs.py` → schreibt
  `extensions.conf` + `pjsip.conf`; installiert wird nach `/etc/asterisk/`.
- **Module:** AudioSocket-Module liegen in `/usr/lib/<arch>-linux-gnu/asterisk/modules/`;
  die Distro-Originale in `/root/asterisk-module-backup-22.5.2/` (Sicherung vor dem Ersatz).
- **Wiederaufbau der Breitband-Module (vollstaendig, offline):**
  `$HERMES_HOME/asterisk/wideband-audiosocket/` enthaelt `build.sh`, den Upstream-Tarball
  `asterisk22.tar.gz` und die gebauten `.so`-Dateien. `./build.sh` baut nur,
  `sudo ./build.sh --install` sichert die Originale, installiert und laedt die Module in
  Abhaengigkeitsreihenfolge neu. Kein Netzzugriff noetig.
- **Rohanalyse-Skripte** (Diagnose, nicht Dauerbetrieb): `$HERMES_HOME/scripts/`
  (`tone_test.py`, `tone_send.py`, `audiosocket_probe.py`, `as_test*.py`, `stt.py`,
  `stt_realtime_test.py`, `sip_announce.py`, `sip_invite_probe.py`, `fonial_probe.sh`).

## 2. Tagesbetrieb

```bash
# Bruecke: Status / Start / Stop / Log
systemctl --user is-active hermes-realtime-bridge
systemctl --user restart hermes-realtime-bridge     # nach Code- oder rt-bridge.env-Aenderung
journalctl --user -u hermes-realtime-bridge -f

# Registrierung + Kanaele
sudo asterisk -rx "pjsip show registrations"
sudo asterisk -rx "core show channels concise"      # leer = kein Gespraech

# Anruf ausloesen (Test; funktioniert zuverlaessig)
TARGET=$(grep -oP '^handy=\K.*' $HERMES_HOME/sip-targets.env | tr -d ' ')
sudo asterisk -rx "channel originate PJSIP/${TARGET}@fo-endpoint extension s@ai"

# Auflegen / aufraeumen
sudo asterisk -rx "channel request hangup all"
```

Beobachten waehrend des Gespraechs:

- `sudo asterisk -rx "pjsip show channelstats"` → Codec + RX/TX-Pakete; gesund ist
  **G.722 mit beiden Zaehlern > 0 und `Lost 0`**.
- `journalctl --user -u hermes-realtime-bridge` → `Anrufer: …` ist die Live-Transkription
  der Gegenseite, `Agent: …` der gesprochene Text der KI, `… an KI: X s | von KI: Y s`
  der Mengenfluss, `[AudioSocket] Ende: …` die Schlussbilanz.
- Antwortet statt des Menschen eine Netzansage oder Mailbox, steht deren Text im
  `Anrufer:`-Eintrag (z. B. „Ruf kann derzeit nicht entgegengenommen werden“) — nicht als
  Nutzerfeedback fehldeuten.

## 3. Persona, Stimme, Modell

`$HERMES_HOME/rt-bridge.env`:

- `HERMES_RT_INSTRUCTIONS` — Systemanweisung der Stimme. Enthaelt bewusst Selbstwissen
  (wer Hermes ist, welcher Stack hier laeuft), weil die Realtime-Sitzung **keinen**
  Zugriff auf Gedaechtnis, Skills oder Dateien hat.
- `HERMES_RT_GREETING` — Auftrag fuer die erste Aeusserung (der Angerufene soll nicht ins
  Leere sprechen).
- `HERMES_RT_MODEL` (Standard `gpt-realtime-2.1`), `HERMES_RT_VOICE` (`marin`).

Nach Aenderung: `systemctl --user restart hermes-realtime-bridge`. Grenzen des Modells:
siehe Abschnitt „Die KI weiss zu wenig“ unten.

## 4. Dialplan aendern

```bash
cd $HERMES_HOME/asterisk
sudo HOME=/home/ubuntu python3 gen_configs.py     # HOME ist noetig, sonst fehlschlagend
sudo cp extensions.conf pjsip.conf /etc/asterisk/
sudo asterisk -rx "dialplan reload"
sudo asterisk -rx "dialplan show ai"              # Gegenprobe
```

- `[ai]` = produktiver Weg: `Answer()` + `Dial(AudioSocket/127.0.0.1:9092/${AS_UUID}/c(slin16),…)`.
- `[ai-rtp]` = UnicastRTP-Variante, **defekt** (nur Diagnose).
- `[ai-as]` (8 kHz zurueck) und die `rtc-io`/`rtp-*`/`tone-io`-Kontexte sind Testaufbauten.
- Nur ein Brueckenprozess darf auf **9092** (AudioSocket) hoeren, sonst `Errno 98`;
  UnicastRTP nutzt 9094.

## 5. Audioqualitaet pruefen und begruenden

- Soll: **16 kHz in beide Richtungen** (Anbietertrunk kann G.722 = 16 kHz, kein Opus).
- Beweis fuer 16 kHz hin zur KI: Logzeile `eingehendes Paket: 640 Byte (20 ms bei 16000 Hz)`
  (= 32 000 Byte/s). 320-Byte-Frames waeren 8 kHz.
- Beweis fuer den Rueckweg: `pjsip show channelstats` (G.722, RX/TX > 0, 0 Lost) plus
  `von KI: X s` in der Schlussbilanz.
- Messmethode ohne Telefonat: `channel originate AudioSocket/127.0.0.1:9092/<uuid>/c(slin16)
  application Dial Local/s@rtc-io` — die Lokalseite spielt eine Frage, `[rtc-io]` nimmt auf.
- Grundlagen, Build-Rezept fuer die Breitband-Module und die UnicastRTP-Fehlmessung:
  `references/audio-quality-and-codecs.md`; Wire-Format/Details: `references/realtime-bridge.md`.

Nach einem `apt upgrade` von Asterisk pruefen, ob das Paket die selbstgebauten Module
ueberschrieben hat (`module show like audiosocket`; Gegenprobe
`strings <Modulpfad>/res_audiosocket.so | grep ast_format_slin16` — fehlt der Treffer, ist
wieder das schmalbandige Paketmodul aktiv). Neu installieren mit
`sudo $HERMES_HOME/asterisk/wideband-audiosocket/build.sh --install`.
Grundlagen und Messungen: `references/audio-quality-and-codecs.md`.

## 6. Die KI weiss zu wenig (Stand Nov 2026)

Die Realtime-Sitzung bekommt nur `instructions` + Greeting; sie hat **keine** Werkzeuge
(`grep '"tools"' realtime_bridge.py` → 0) und keinen Zugriff auf Gedaechtnis oder Dateien.
Deshalb beantwortet sie Fragen zum eigenen Aufbau falsch, wenn das nicht in den Instruktionen
steht. Ausbaustufen: (a) Selbstwissen in `HERMES_RT_INSTRUCTIONS` (erledigt, Abschnitt 3),
(b) `session.tools` als **Funktionswerkzeug** — die Bruecke fuehrt es lokal aus und schiebt
das Ergebnis zurueck (kein Firewall-Eingriff, im Gegensatz zu MCP-Werkzeugen, die OpenAI
selbst aufruft), z. B. ein Werkzeug „frage die volle Hermes-Sitzung“ fuer schwere Fragen.

## 7. Fallen, die schon Geld/Zeit gekostet haben

- **`voice_call.py` ist kein Erfolgsindikator**: es meldet `Warnung: Call-File nicht lesbar
  abgelegt` und teils `200 OK`, ohne zu waehlen (Spool leer, kein CDR) — manchmal waehlt es
  aber doch. Erfolg immer in `full.log`/CDR/channelstats pruefen, fuer Tests direkt
  `channel originate` benutzen.
- **Modulname:** `res_audiosocket.so` (ohne Unterstrich); `module show like audio_socket`
  findet nichts und taugt nicht als Anwesenheitspruefung.
- **`response_cancel_not_active`** ist ein harmloses Wettrennen (Antwort war schon fertig),
  kein Defekt — im Log als Notiz gefuehrt.
- **Kanal ohne Bruecken-ID = klingelt noch**, mit Bruecken-ID = abgenommen; die Bruecke startet
  die Sitzung erst beim Abnehmen.
- **Notrufnummern nie** — keine Ausnahmen.
