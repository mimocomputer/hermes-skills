# Audio quality on a SIP/PBX number — measured (Fonial/Plusnet, Nov 2026)

## What the provider actually carries

- The provider's answer SDP: `m=audio … RTP/AVP 9 102` → `a=rtpmap:9 G722/8000` + telephone-event. **G.722 (16 kHz) is selected** when offered.
- **Opus is refused**: offering *only* `opus` makes the call fail before ringing with `488 Not Acceptable Here` — the trunk does not carry Opus. 48 kHz wideband is therefore unreachable on the phone leg; G.722 is the ceiling and a real step up from G.711.
- Keep `opus` in the endpoint's `allow=` list anyway: it costs nothing (the provider ignores what it cannot use) and it is the right codec for direct SIP peers — WebRTC clients, a media bridge, or OpenAI's leg. Make the list env-driven (`FO_CODECS`, default `opus,g722,ulaw,alaw`) so an experiment does not need a code edit.
- Verify the negotiated codec from the log, not from hope: `core show channels` / `Topology: … (g722)` lines in `full.log`, and `Unable to open …` errors when the prompt cannot be delivered.

## AI telephony: the 8 kHz ceiling was a module limit, and it is fixed (Nov 2026)

The Debian `res_audiosocket` 22.5.2 takes only frame type `0x10`, which it reads as 8 kHz —
16 kHz data tagged `0x10` plays at half speed (deep voice).
`strings /usr/lib/aarch64-linux-gnu/asterisk/modules/res_audiosocket.so | grep slin` showed
only `ast_format_slin`, no SLIN12/SLIN16 kinds.

**Solved by building the wideband modules out of the upstream Asterisk 22 branch** (recipe
below): after swapping in `res_audiosocket.so` + `chan_audiosocket.so` — Debian originals
backed up in `/root/asterisk-module-backup-22.5.2`, loaded in dependency order res → chan →
app — the channel speaks kind `0x12` (slin16) in *both* directions. Verified on a real
110-second call: 640-byte frames per 20 ms into the bridge (= 32 000 byte/s, i.e. 16 kHz),
the same back out, `pjsip show channelstats` G.722 172/172 packets, 0 lost, 0 % jitter, and
the user confirming the audio was clearly better and no longer deep. The bridge reads kinds
`0x10`–`0x18` against a rate table (`AUDIOSOCKET_RATES`) and converts anything else to its
16 kHz working rate, so a stock module only degrades — never breaks — the audio.

**Do not reach for `UnicastRTP` as the wideband replacement — its read direction is broken
in this build.** Measured with a bridged `AudioSocket` peer as the instrument: 381 packets
sent into the unicast leg from the expected source port, Asterisk logs every one as
received (`Got RTP packet from 127.0.0.1:9094`, no strict-RTP drop, bridge is
`basic/simple_bridge`, translation present), and the peer receives **0 bytes**. The frames
never leave the channel into the bridge. Only the *write* direction (Asterisk → the socket)
works, which is why local prompt-playback tests pass while real calls stay silent. Debugging
aids that lie: `Echo` as a bridged callee, `Record`/`MixMonitor` on a `Local` leg. Use an
AudioSocket peer you control as the measuring instrument.

**Real fix for 16 kHz both ways: build the wideband AudioSocket module from upstream.** The
Asterisk 22 *branch* has `AST_AUDIOSOCKET_KIND_AUDIO_SLIN12/SLIN16` (commit cb5b22db) and a
matching `channels/chan_audiosocket.c`; the Debian 22.5.2 package predates both. Build both
modules out-of-tree against the installed `asterisk-dev` headers — the two defines below are
what the `#error "Externally compiled modules must declare AST_MODULE_SELF_SYM"` and
`AST_MODULE undeclared` failures actually want, and the tarball include dir must come
*before* `/usr/include` so the new kind constants are visible:

```bash
gcc -fPIC -O2 -I/tmp/asterisk-22/include -I/usr/include -shared -o res_audiosocket.so \
    /tmp/asterisk-22/res/res_audiosocket.c \
    -DAST_MODULE_SELF_SYM=__internal_res_audiosocket_self -DAST_MODULE='"res_audiosocket"'
```

Then the bridge must handle kinds `0x12`/`0x13` in both directions instead of assuming
`0x10` = 8 kHz; it now tags its own output `0x12` and gets slin16 back. The trunk's own
ceiling stays G.722.

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

## Placing a test call when the call-file path misbehaves

`voice_call.py` prints `Warnung: Call-File nicht lesbar abgelegt` and still reports
`final response: 200 OK` — the warning is **not** fatal (observed calls connect fine with
it). It is equally useless as a success signal: in one case the script exited 0, the spool
dir was empty and no CDR line ever appeared, so the call never happened. Never judge an
attempt by the script's exit status — check `/var/log/asterisk/cdr-csv/Master.csv`,
`core show channels` and the bridge journal, or watch for the outgoing
`INVITE sip:<nummer>@…` in `full.log`. Direct originate bypasses the spool and always works:

```bash
sudo asterisk -rx "channel originate PJSIP/<nummer>@fo-endpoint extension s@ai"
```

It returns immediately; the call runs in the background. Check the outcome with
`pjsip show channelstats` (RX/TX packet counts = audio really flowing both ways) and the
bridge journal (`Anrufer: …` lines = live STT of the far end). A far end that is switched
off or unreachable is answered by the carrier's announcement — the transcript then contains
phrases like "die gewünschte Gesprächsperson ist nicht zu erreichen", so do not mistake that
for user feedback. Kill background `voice_call.py` runs with a bracket pattern
(`pkill -f "[v]oice_call.py"`) so the pattern does not match the killing shell itself.

## TLS transport (needed when a bridge or a hosted platform requires `sips:`)

- Transport block that loads on Debian/Ubuntu Asterisk 22: `type=transport`, `protocol=tls`, `bind=0.0.0.0:5061`, `cert_file=`, **`priv_key_file=`** (a `key_file` option does not exist and makes sorcery drop the whole transport), optionally `method=tlsv1_2`.
- The cert and key must be readable **by the asterisk user** — otherwise: `priv_key_file … is either missing or not readable` and the transport silently does not appear in `pjsip show transports`.
- Self-signed is fine for a transport that only acts as a client; generate with `openssl req -x509 -newkey rsa:2048 -nodes -days 2`.
- Note for testing: some distro OpenSSL builds refuse TLS 1.2 *client-side*, so a loopback `openssl s_client` check can fail for reasons that have nothing to do with Asterisk — pjproject exports its TLS layer (e.g. 19 `ssl_sock` symbols in `libasteriskpj.so.2`) and speaks TLS 1.2. Prove the path with a real peer instead.

## Provider-side network plumbing (Oracle Cloud example)

The VCN security list (queried with the OCI CLI, which is configured on the host) contained ingress for TCP 22/80/443 and ICMP only — no UDP. Any design where the *other* side initiates (a hosted realtime platform dialling into the Asterisk bridge) therefore needs both the local packet filter and the cloud security list opened for TCP 5061 plus the media UDP range, ideally restricted to the platform's published CIDRs.
