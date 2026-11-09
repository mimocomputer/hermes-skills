# Realtime voice over a SIP/PBX number — feasibility and the TLS bridge

Measured on Asterisk 22, Debian/Ubuntu on ARM, with a cloud-PBX SIP user on a provider trunk that offers plain UDP/G.711 only.

## Provider leg: what the measurements say

- UDP/5060 answers (`200 OK` to an unauthenticated OPTIONS) — that is the working signalling path.
- **TCP/5060 and TCP/5061 toward the provider are closed**, for both the hostname and the pinned proxy IP. So there is no TLS (no `sips:`), no SRTP negotiation, on that leg.
- What that rules out is the *provider leg only*: the provider cannot be made to speak TLS/SDES-SRTP/Opus. It does **not** rule out a hosted platform that needs those on the far side, because the missing capability can come from an intermediate you control — a PBX that answers the provider in plain UDP/G.711 and dials the platform over TLS/SRTP/Opus. Decide per hop, not per route.

## Asterisk as the TLS/SRTP bridge (verified on the Debian package)

Bring a TLS transport up beside the working UDP one. No rebuild is needed: the vendored pjproject links OpenSSL and exports `ssl_sock` symbols.

```
[transport-tls]
type=transport
protocol=tls
bind=0.0.0.0:5061
cert_file=/etc/asterisk/keys/<name>.crt
priv_key_file=/etc/asterisk/keys/<name>.key
```

- **The option is `priv_key_file`, not `key_file`.** A wrong field name fails the whole object silently: `pjsip show transports` just omits it, and the reason sits one or two lines *before* `res_sorcery_config.c: Could not create an object of type 'transport'` in `full.log` (`config_options.c: Could not find option suitable for category …`). Grep around the sorcery error instead of guessing.
- **Cert and key must be readable by the service user**: `chown asterisk:asterisk`, `chmod 640` on both files and at least `750` on their directory, or the transport reports `<file> is either missing or not readable` and never loads.
- Probe without touching the generated `pjsip.conf`: keep the block in its own file and append `#include <probe>.conf` once — removing it later is a one-line undo.
- Verify with `ss -ltnp | grep 5061` and `pjsip show transports`, then re-check `pjsip show registrations`: the provider registration must still read `Registered` after the reload.
- **A failed loopback handshake proves nothing on its own.** A modern OpenSSL client can refuse TLS 1.2 outright (`UNSUPPORTED_PROTOCOL`, even with `-tls1_2` and a neutral config) while pjproject's transport speaks TLS 1.2 and rejects TLS 1.3 server-side — so a local `s_client`/`ssl` test fails against a healthy transport. Report "listening plus TLS-capable library present" as the local result and settle version/cipher against the real peer, where `method`/`cipher` belong explicitly.
- Firewall consequence for a platform that dials *you*: host firewalls are often allowlists (SSH/HTTP/HTTPS only). Open the TLS port plus the peer's SRTP/UDP media ranges, and check the cloud security list too. When *you* dial the platform instead, the media rides the established conntrack entry and needs no inbound rule.

## Hosted side (vendor documentation, not measured here)

- OpenAI Live API, outbound: `POST /v1/live/sessions` with `transport.type: "sip"`, `transport.destination` (E.164; SIP URIs unsupported), `transport.trunk.provider_url` — which must be `sips:host:5061` — `transport.trunk.auth.type: digest` plus username/password, and `caller_number` in E.164. The inbound shape is the mirror image: point the provider's trunk at `sip:<PROJECT_ID>@sip.api.openai.com;transport=tls` and accept the incoming webhook. Local hostnames and literal private/local IPs are rejected, so a resolvable public hostname is required.
- OpenAI requires SRTP for media and publishes its media ranges (`13.79.45.80/28`, `23.98.140.64/28`, `40.67.149.176/28`, `40.83.204.240/28`); signalling is TCP/TLS on 5061 only.
- Model/endpoint matrix: `gpt-live-1` belongs to the Live API (`/v1/live/sessions`); `gpt-realtime` (deprecated but still functional) and `gpt-realtime-1.5` are served on `/v1/realtime` and can carry SIP calls. An existing API project can therefore reach a SIP-capable realtime model without buying a new product — the open question is whether that project has the SIP connector enabled, which is worth probing with a key before designing around it.
- A plain model gateway (OpenRouter and similar) is not a duplex realtime path: audio in/out request-response plus a TTS endpoint, no live WebSocket session. Fine for a cascade, useless as a hosted conversational agent.

## Media path inside Asterisk on Debian/Ubuntu

- **Name trap, verified:** the module is `res_audiosocket.so` (no underscore between *audio* and *socket*), so `module show like audio_socket` reports "0 modules" on a box that *has* it — check `module show like audiosocket`. The `asterisk-modules` package does ship AudioSocket (`dpkg -S` → `res_audiosocket.so`, `chan_audiosocket.so`, `app_audiosocket.so`), but the packaged build is narrowband-only (kind `0x10` = 8 kHz).
- `res_external_media.so` (ARI ExternalMedia) is genuinely **not** packaged (`dpkg -L asterisk | grep res_external_media` → nothing), so that route needs a self-build.
- It **does** ship `res_speech_aeap.so` + `res_speech.so` + `app_speech_utils.so` (AEAP — Asterisk External Application Protocol — the in-package way to stream call audio to an external process over a WebSocket), plus `res_srtp.so` and `codec_opus_open_source.so` with `res_format_attr_opus.so` for transcoding to a platform that insists on Opus.
- Alternatives: compile the missing modules from the Asterisk source tree, or stay with the store-and-forward loop (see `references/local-asterisk.md`).

## ElevenLabs Scribe v2 Realtime — works directly on telephone audio (measured)

Endpoint: `wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime&audio_format=ulaw_8000&commit_strategy=vad`, auth header `xi-api-key`.

- **`audio_format=ulaw_8000` is supported** — exactly the G.711 μ-law an Asterisk call carries, so no transcoding is needed on the media path.
- Send 20 ms frames (160 bytes) as `{"message_type":"input_audio_chunk","audio_base_64":"…"}` ~50×/s; finish with `commit: true`.
- Measured on a 14.9 s recording of a real phone call: `session_started` in 0.17 s, first partial ~0.2–0.5 s behind the speaker, new partials roughly every second, final `committed_transcript` **0.25 s** after the last chunk, clean `1000` close. Latency is fine for a conversational loop.
- **Pin the language** (`language_code=de`): without it a German call can open with a mis-detected token in another script.
- A normal session close raises `websockets.exceptions.ConnectionClosedOK` — catch it, do not treat it as an error.
- Self-test harness: `scripts/stt_realtime_test.py <file> [--fmt ulaw|pcm16] [--speed N]` streams a file in real time and timestamps every event, so latency and vocabulary are verifiable without touching the phone system.
