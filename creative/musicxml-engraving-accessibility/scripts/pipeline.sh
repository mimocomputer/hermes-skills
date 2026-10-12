#!/bin/bash
# Full build pipeline: MusicXML -> MSCZ -> patch style -> render -> MSCZ/PDF/MIDI
set -e
cd /home/ubuntu/music-scores/lobe-den-herren
MS=~/.local/bin/musescore4
NAME=${1:-DAISY}
SRC="out/Lobe-den-Herren-$NAME.musicxml"

echo "== build musicxml"
.venv/bin/python scripts/build_musicxml.py "$(echo $NAME | tr 'A-Z' 'a-z')" "$SRC"

echo "== musicxml -> mscz"
rm -f "out/Lobe-den-Herren-$NAME.mscz"
timeout 300 xvfb-run -a $MS -o "out/Lobe-den-Herren-$NAME.mscz" "$SRC" >/dev/null 2>&1

echo "== patch style (hide empty staves)"
.venv/bin/python scripts/patch_mscz.py "out/Lobe-den-Herren-$NAME.mscz"

echo "== render pdf + midi + mxl"
timeout 300 xvfb-run -a $MS -o "out/Lobe-den-Herren-$NAME.pdf" "out/Lobe-den-Herren-$NAME.mscz" >/dev/null 2>&1
timeout 300 xvfb-run -a $MS -o "out/Lobe-den-Herren-$NAME.mid" "out/Lobe-den-Herren-$NAME.mscz" >/dev/null 2>&1
timeout 300 xvfb-run -a $MS -o "out/Lobe-den-Herren-$NAME.mxl" "out/Lobe-den-Herren-$NAME.mscz" >/dev/null 2>&1
ls -la out/ | grep "$NAME"
