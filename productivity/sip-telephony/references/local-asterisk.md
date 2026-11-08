# Local Asterisk stack — call files, dialplan, two-way loop (measured)

Depth for step 7 of the skill. Everything here was measured on Asterisk 22 on an ARM Ubuntu host with a Fonial (Plusnet) SIP user.

### 7. Two-way loop without a media bridge (measured)

Cheapest working conversation path is **store and forward over two calls**, no AudioSocket/ARI needed:

1. `Playback(custom/frage)` → `Record(/tmp/hermes_call/answer.wav,3,15)` (args are `filename, silence, maxduration`) → a short closing `Playback` so the channel does not drop the file, then `Hangup`.
2. Transcribe the WAV with **ElevenLabs Scribe** when an ElevenLabs key already exists for TTS: `POST https://api.elevenlabs.io/v1/speech-to-text`, header `xi-api-key`, multipart `file=@answer.wav` + `model_id=scribe_v1`; the answer carries `text`, `language_code` (`deu`) and `language_probability`, so German needs no configuration.
3. Reply with a second originated call playing the generated TTS.

Gotchas that cost a round of debugging:

- **`channel originate` returns the moment the callee answers**, while the dialplan keeps running — checking for the recording right after the command made a successful call look like a no-answer. Poll `core show channels` until your endpoint disappears, then read the file.
- Asterisk writes recordings as its own user: `chmod 644` (or read via `sudo`) before the agent's own user transcribes them.
- Write recordings under `/tmp/<dir>` with mode `1777`, not into the agent's home — the asterisk user must be able to create the file.
- A `Record()`ed call that the callee hangs up mid-recording **loses all audio**; keep a closing playback in the dialplan.
- Enable `[general] enable=yes` in `cdr.conf` to get one `ANSWERED`/`billsec` line per leg in `/var/log/asterisk/cdr-csv/Master.csv` — that is the artifact that proves a two-way test really happened.

### 7a. Caller ID presentation — use call files, not `channel originate` (measured)

- `channel originate` builds the channel with **no** caller ID, so Asterisk sends `From: "Anonymous" <sip:...>`. Providers and handsets render that as *unbekannte Nummer*, and Fonial even answered `480 Temporarily Unavailable` with `X-Hangup-Reason: Target not found` when the CLI was absent entirely.
- Place the call with a **call file** in `/var/spool/asterisk/outgoing/` (written to a temp name and moved in, owned by `asterisk`):

  ```
  Channel: PJSIP/+491701234567@endpoint
  CallerID: Name <+491701234567>
  SetVar: PROMPT=myfile
  MaxRetries: 0
  WaitTime: 45
  Context: mycontext
  Extension: s
  Priority: 1
  Archive: yes
  ```

  Only then does the INVITE go out as `From: <sip:NUMBER@domain>` with no display name — matching what a manually built client sends, and what the carrier presents as the CLIP number. (`Archive: yes` keeps a copy in `outgoing_done` for debugging; `SetVar` is the clean way to pass per-call parameters into the dialplan.)
- `channel originate` also returns when the callee answers, while the dialplan keeps running — poll `core show channels` for the endpoint to appear *and* disappear before reading recordings or CDRs.
- Deliver the call file with `cp` + `chown <asterisk-user>` + `chmod 640`; `install -o/-g` into the spool intermittently fails with `install: metadata error`, leaving an unreadable file that `pbx_spool` deletes with a `Permission denied` warning, so the call silently never happens.
- A "call file not readable" warning from your own check is **not** proof the call failed: if `pbx_spool` consumes the file instantly, a `test -r` on the path afterwards fails while the call goes out normally. Always confirm the outcome from the SIP response / CDR, not from the delivery check.
- Reading the destination back out of an archived call file (`outgoing_done/`, `Archive: yes`) is a handy way to derive format variants (E.164 / `00…` / national) without retyping the number — but it **propagates an earlier typo indefinitely**. Never treat a self-derived destination as the source of truth: before blaming the provider for a per-destination failure, compare your dial string in code against an authoritative string (a call-log line the user can read, the portal's number list). Masked numbers in tool output make eyeballing useless — do the comparison in a shell/Python variable, print only booleans, lengths and differing character positions (`^^^..`), and compare against digit groups stored in separate variables so the mask does not corrupt your own argument.
- **A persistent per-destination `480` is very often simply a wrong number.** Measured case: a 12-character dial string ending in the right last four digits produced `480 … Target not found` for a whole evening, while the same destination answered `200 OK` the moment the number taken from the user's own call log was dialled (14 characters — the derived string was two digits short). Cost of the mistake: a full evening of config archaeology plus a portal audit, all of which came back clean. Establish the destination first, then the provider.


### 7b. Local stack on the agent host (measured, Asterisk 22 / Debian-Ubuntu ARM)

`apt-get install -y asterisk` gives a working PJSIP stack; no sound card needed for `Playback`. Two traps cost most of the time:

- **pjlib's bundled resolver fails on zones with 12 A-records and no AAAA**: `pjsip_resolver.c: Resolution completed - 0 viable targets` → registration ends as `503 No answer record in the DNS response (PJLIB_UTIL_EDNSNOANSWERREC)`. `dig` resolves the same name fine; only Asterisk's resolver is broken. Fix: pin one SRV/A target by IP in the config generator (`dig +short SRV _sip._udp.<host>` → first target → its first A record) and use that IP in `server_uri` and the aor `contact`, keeping the hostname in `client_uri`/`from_domain`. Regenerate with a script that reads `sip.env` so the password never passes through stdout.
- **Behind NAT** (Oracle: private `10.x` + 1:1 public IP) set `external_media_address` / `external_signaling_address` to the public IP and list `local_net` for the private ranges, plus `direct_media=no`, `rtp_symmetric=yes`, `force_rport=yes`, `rewrite_contact=yes`.
- **Never let the pinned IP leak into the Request-URI.** Substituting the resolved IP in the aor `contact` (the obvious fix for the resolver trap above) makes every outbound call fail with **`403 Forbidden`** on providers whose softswitch routes by R-URI domain — while the INVITE still authenticates (a `407` precedes the `403`, `Content-Length: 0`, no reason phrase). Correct shape: `contact=sip:<provider-host>:5060` (hostname, for the R-URI) **plus** `outbound_proxy=sip:<pinned-ip>:5060\;lr` on the endpoint (for the wire), with the `type=registration` object pointing at the IP. Symptom to remember: same config that gets `403` on `sip:<number>@<ip>` answers `100 Trying → 180 Ringing → 200 OK → Playback` on `sip:<number>@<host>`.
- Enable a text SIP trace only when needed: uncomment `full.log => ...debug,verbose...` in `/etc/asterisk/logger.conf`, `logger reload`, `pjsip set logger on`, then grep `/var/log/asterisk/full.log`. `pjsip show registrations` gives the one-line status (`Registered (exp. 1545s)` / `Rejected`).
- Test calls headless with `asterisk -rx "channel originate PJSIP/<dest>@<endpoint> extension s@<context>"`; the dialplan plays the announcement. Read the outcome from the log line `Response is <code>` instead of parsing the CLI output.
- **Turn on CDRs before claiming a call succeeded**: uncomment `enable=yes` under `[general]` in `/etc/asterisk/cdr.conf`, `module reload cdr_csv.so`, then read `/var/log/asterisk/cdr-csv/Master.csv`. A line with `ANSWERED` and `billsec > 0` is the difference between "the provider accepted the INVITE" and "the callee actually heard the announcement" — a provider can answer, ring, and still drop the media.
- `Playback(custom/<name>)` resolves against the sounds directory (`/usr/share/asterisk/sounds/`); install the TTS file there as 8 kHz mono `pcm_s16le` WAV owned by `asterisk`: `install -o asterisk -g asterisk -m 644 ansage.wav /usr/share/asterisk/sounds/custom/`. A whole POC call is then: `ffmpeg -i tts.mp3 -ar 8000 -ac 1 -c:a pcm_s16le ansage.wav` → originate → CDR says `ANSWERED`.
- **`pbx_spool` kann den Anruf ein zweites Mal waehlen — trotz `MaxRetries: 0`.** Beobachtet
  im echten Telefonat: Kanal stand, Gespraech lief, und 60 s nach dem ersten Versuch kam ein
  **zweiter Anruf** auf demselben Handy an (`StartRetry` im Log, zweite CDR-Zeile mit eigener
  `uid`). Vorausgegangen war unmittelbar nach `Filename: <file>` die Warnung
  `Unable to set utime on <file>: Operation not permitted` — das Modul markiert einen Versuch
  ueber die Dateizeit; gelingt das nicht, gilt die Datei beim naechsten Scan (nach `RetryTime`)
  wieder als offen und wird erneut gewaehlt. Fix (beides zusammen): die Call-Datei aus dem
  Spool **entfernen, sobald der eigene Endpoint in `core show channels` auftaucht**, und
  `RetryTime: 3600` setzen. Gegenprobe: kein `StartRetry` fuer diese Datei im `full.log`.
- A mature stack also tells the *provider's* verdict apart from your own signalling: `407` before/after `403` means auth is fine and the **account policy** refuses (`403 Forbidden`, `Content-Length: 0`, no reason phrase). Expect 403 when the SIP user has no outbound right and stop probing dial formats — see the next pitfall.

