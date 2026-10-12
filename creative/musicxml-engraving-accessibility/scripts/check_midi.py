"""Check the exported MIDI: total length and repeat unfolding."""
import sys
import mido

path = sys.argv[1]
mid = mido.MidiFile(path)
print('ticks_per_beat', mid.ticks_per_beat, 'tracks', len(mid.tracks))
total = 0
for i, tr in enumerate(mid.tracks):
    t = sum(m.time for m in tr)
    total = max(total, t)
    print(f'  track {i}: {t} ticks, events={len(tr)}')
print('longest track ticks:', total)
beats = total / mid.ticks_per_beat
print('beats:', beats, '=> quarter-note beats; measures (3/4):', beats / 3)
# expected: 74 measures + 21 repeated measures = 95 measures = 285 beats
print('expected beats (95 measures x 3):', 95 * 3)

# tempo events
for i, tr in enumerate(mid.tracks):
    for msg in tr:
        if msg.type == 'set_tempo':
            print('tempo', mido.tempo2bpm(msg.tempo), 'bpm on track', i)
            break
