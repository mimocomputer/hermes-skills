#!/usr/bin/env python3
"""Scribe v2 Realtime gegen eine Audiodatei testen (Latenz der Partial-Transkripte messen).

    stt_realtime_test.py <audio> [--ulaw|--pcm16] [--speed 1.0]

Schickt die Datei in 20-ms-Häppchen in Echtzeit an
wss://api.elevenlabs.io/v1/speech-to-text/realtime und protokolliert, wann
partial_transcript / committed_transcript ankommen. Damit ist die Pipeline
Telefonie-tauglich (G.711 μ-law, 8 kHz) prüfbar, bevor Asterisk im Spiel ist.
"""
import argparse, asyncio, base64, json, os, re, subprocess, sys, time
from pathlib import Path
import websockets

FFMPEG = Path.home() / ".hermes/tools/ffmpeg-9.0.1-linux-arm64/bin/ffmpeg"
URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"


def key():
    m = re.search(r"^ELEVENLABS_API_KEY=(.*)$", (Path.home() / ".hermes/.env").read_text(), re.M)
    return (os.environ.get("ELEVENLABS_API_KEY") or (m.group(1).strip() if m else "")).strip()


def to_ulaw(src, fmt):
    out = Path("/tmp/_rt_audio.raw")
    codec = "pcm_mulaw" if fmt == "ulaw" else "pcm_s16le"
    r = subprocess.run([str(FFMPEG), "-y", "-i", src, "-ar", "8000", "-ac", "1", "-f", "s16le" if fmt != "ulaw" else "mulaw", str(out)],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg: " + r.stderr[-300:])
    return out.read_bytes()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--fmt", default="ulaw", choices=["ulaw", "pcm16"])
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()

    if a.fmt == "ulaw":
        audio_format, chunk = "ulaw_8000", 160          # 20 ms @ 8 kHz
    else:
        audio_format, chunk = "pcm_16000", 640          # 20 ms @ 16 kHz

    data = to_ulaw(a.audio, a.fmt)
    url = f"{URL}?model_id=scribe_v2_realtime&audio_format={audio_format}&commit_strategy=vad&include_timestamps=true"
    t0 = time.time()
    sent_end = None
    print(f"Datei {a.audio}: {len(data)} Bytes, Format {audio_format}, "
          f"{len(data)/chunk*20/1000:.1f} s Audio, Tempo {a.speed}x", flush=True)

    async with websockets.connect(url, additional_headers={"xi-api-key": key()}, max_size=8 * 1024 * 1024) as ws:
        async def send():
            nonlocal sent_end
            for i in range(0, len(data), chunk):
                await ws.send(json.dumps({"message_type": "input_audio_chunk",
                                          "audio_base_64": base64.b64encode(data[i:i + chunk]).decode()}))
                await asyncio.sleep(0.020 / a.speed)
            await ws.send(json.dumps({"message_type": "input_audio_chunk", "audio_base_64": "", "commit": True}))
            sent_end = time.time() - t0
            print(f"[{sent_end:6.2f}s] Audio komplett gesendet + commit", flush=True)

        async def recv():
            first_partial = None
            while True:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                except asyncio.TimeoutError:
                    print("  (20 s keine Nachricht — Verbindung still)", flush=True)
                    break
                except websockets.exceptions.ConnectionClosedOK:
                    print("  (Server hat die Session normal geschlossen)", flush=True)
                    break
                t = time.time() - t0
                mt = msg.get("message_type")
                if mt == "partial_transcript":
                    if msg.get("text"):
                        if first_partial is None:
                            first_partial = t
                            print(f"[{t:6.2f}s] ERSTES PARTIAL", flush=True)
                        print(f"  [{t:6.2f}s] partial: {msg['text']}", flush=True)
                elif mt == "committed_transcript":
                    print(f"  [{t:6.2f}s] COMMIT: {msg.get('text')}", flush=True)
                elif mt in ("session_started", "input_error", "error"):
                    print(f"  [{t:6.2f}s] {mt}: {str(msg)[:200]}", flush=True)
                    if mt in ("input_error", "error"):
                        break
        await asyncio.gather(send(), recv())

asyncio.run(main())
