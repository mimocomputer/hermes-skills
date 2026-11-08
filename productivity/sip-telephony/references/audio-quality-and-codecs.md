# Audio quality on a SIP/PBX number — measured (Fonial/Plusnet, Nov 2026)

## What the provider actually carries

- The provider's answer SDP: `m=audio … RTP/AVP 9 102` → `a=rtpmap:9 G722/8000` + telephone-event. **G.722 (16 kHz) is selected** when offered.
- **Opus is refused**: offering *only* `opus` makes the call fail before ringing with `488 Not Acceptable Here` — the trunk does not carry Opus. 48 kHz wideband is therefore unreachable on the phone leg; G.722 is the ceiling and a real step up from G.711.
- Keep `opus` in the endpoint's `allow=` list anyway: it costs nothing (the provider ignores what it cannot use) and it is the right codec for direct SIP peers — WebRTC clients, a media bridge, or OpenAI's leg. Make the list env-driven (`FO_CODECS`, default `opus,g722,ulaw,alaw`) so an experiment does not need a code edit.
- Verify the negotiated codec from the log, not from hope: `core show channels` / `Topology: … (g722)` lines in `full.log`, and `Unable to open …` errors when the prompt cannot be delivered.

## Prompt files: install raw slin16, not a 16 kHz WAV

A 16 kHz `.wav` in `sounds/custom/` produced a **silent, instantly hung-up call**: on a G.722 channel Asterisk looks for `custom/<name>.g722` first, gives up instead of falling back, logs `Unable to open custom/<name> (format (g722)): No such file or directory` + `Playback failed`, and the CDR shows `ANSWERED` with `billsec 0.001`.

Working recipe — install both formats, no transcoding needed in either direction:

```bash
ffmpeg -y -i prompt.mp3 -ar 16000 -ac 1 -f s16le /tmp/p.sln16   # raw 16 kHz → .sln16
ffmpeg -y -i prompt.mp3 -ar  8000 -ac 1 -f mulaw /tmp/p.ulaw    # raw 8 kHz µ-law → .ulaw
install -o asterisk -g asterisk -m 644 /tmp/p.sln16 /usr/share/asterisk/sounds/custom/<name>.sln16
install -o asterisk -g asterisk -m 644 /tmp/p.ulaw  /usr/share/asterisk/sounds/custom/<name>.ulaw
```

The write path in the log then reads `setting write format path: slin16 -> g722` and the audio is really 16 kHz. Generate TTS at 16 kHz or higher upstream so the wideband file is not an upsample of an 8 kHz source. Recordings for STT should follow the same principle (`.sln16`, or convert with `ffmpeg -f s16le -ar 16000`); ElevenLabs Scribe Realtime accepts `pcm_16000` as well as `ulaw_8000`.

## TLS transport (needed when a bridge or a hosted platform requires `sips:`)

- Transport block that loads on Debian/Ubuntu Asterisk 22: `type=transport`, `protocol=tls`, `bind=0.0.0.0:5061`, `cert_file=`, **`priv_key_file=`** (a `key_file` option does not exist and makes sorcery drop the whole transport), optionally `method=tlsv1_2`.
- The cert and key must be readable **by the asterisk user** — otherwise: `priv_key_file … is either missing or not readable` and the transport silently does not appear in `pjsip show transports`.
- Self-signed is fine for a transport that only acts as a client; generate with `openssl req -x509 -newkey rsa:2048 -nodes -days 2`.
- Note for testing: some distro OpenSSL builds refuse TLS 1.2 *client-side*, so a loopback `openssl s_client` check can fail for reasons that have nothing to do with Asterisk — pjproject exports its TLS layer (e.g. 19 `ssl_sock` symbols in `libasteriskpj.so.2`) and speaks TLS 1.2. Prove the path with a real peer instead.

## Provider-side network plumbing (Oracle Cloud example)

The VCN security list (queried with the OCI CLI, which is configured on the host) contained ingress for TCP 22/80/443 and ICMP only — no UDP. Any design where the *other* side initiates (a hosted realtime platform dialling into the Asterisk bridge) therefore needs both the local packet filter and the cloud security list opened for TCP 5061 plus the media UDP range, ideally restricted to the platform's published CIDRs.
