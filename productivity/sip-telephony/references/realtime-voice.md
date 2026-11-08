# Realtime voice over a SIP/PBX number — measured feasibility (Asterisk 22, Debian, ARM)

## Transport reality check (re-measured 08.11.2026, Fonial/Plusnet)

- UDP/5060 answers (`200 OK` to an unauthenticated OPTIONS) — that is the working signalling path.
- **TCP/5060 and TCP/5061 are closed** toward both the hostname and the pinned proxy IP. No TLS (thus no `sips:`), no SRTP negotiation.
- Consequence: hosted realtime platforms that demand TLS + SDES-SRTP + Opus for BYO trunks (OpenAI Realtime / GPT-Live with digest credentials, similar LiveKit/Vapi setups) are **not** reachable on such an account. Settle this by measurement before promising them; ask the provider to enable TLS/SRTP if it is a must-have.

## Media path inside Asterisk on Debian/Ubuntu

- The `asterisk-modules` package does **not** contain `res_audio_socket.so` (AudioSocket) or `res_external_media.so` (ARI ExternalMedia). `module show like audio_socket` returning "0 modules" means absent, not unloaded — check the module directory from `core show settings` (`/usr/lib/<arch>-linux-gnu/asterisk/modules`).
- It **does** ship `res_speech_aeap.so` + `res_speech.so` + `app_speech_utils.so`: AEAP (Asterisk External Application Protocol) is the in-package way to stream call audio to an external process over a WebSocket.
- Alternatives: compile the missing modules from the Asterisk source tree, or stay with the store-and-forward loop (section 7 / `references/local-asterisk.md`).

## ElevenLabs Scribe v2 Realtime — works directly on telephone audio (measured)

Endpoint: `wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime&audio_format=ulaw_8000&commit_strategy=vad`, auth header `xi-api-key`.

- **`audio_format=ulaw_8000` is supported** — exactly the G.711 μ-law an Asterisk call carries, so no transcoding is needed on the media path.
- Send 20 ms frames (160 bytes) as `{"message_type":"input_audio_chunk","audio_base_64":"…"}` ~50×/s; finish with `commit: true`.
- Measured on a 14.9 s recording of a real phone call: `session_started` in 0.17 s, first partial ~0.2–0.5 s behind the speaker, new partials roughly every second, final `committed_transcript` **0.25 s** after the last chunk, clean `1000` close. Latency is fine for a conversational loop.
- **Pin the language** (`language_code=de`): without it a German call can open with a mis-detected token in another script.
- A normal session close raises `websockets.exceptions.ConnectionClosedOK` — catch it, do not treat it as an error.
- Self-test harness: `scripts/stt_realtime_test.py <file> [--fmt ulaw|pcm16] [--speed N]` streams a file in real time and timestamps every event, so latency and vocabulary are verifiable without touching the phone system.
