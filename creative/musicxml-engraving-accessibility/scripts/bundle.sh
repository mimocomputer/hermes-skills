#!/bin/bash
# Build the final bundle with manifest
set -e
cd /home/ubuntu/music-scores/lobe-den-herren
bash scripts/pipeline.sh Master >/dev/null 2>&1

mkdir -p out/bundle
cp out/Lobe-den-Herren-Master.mscz out/Lobe-den-Herren-DAISY.mscz \
   out/Lobe-den-Herren-Master.mxl out/Lobe-den-Herren-DAISY.mxl \
   out/Lobe-den-Herren-Master.musicxml out/Lobe-den-Herren-DAISY.musicxml \
   out/Lobe-den-Herren-Master.pdf out/Lobe-den-Herren-DAISY.pdf \
   out/Lobe-den-Herren-Master.mid out/Lobe-den-Herren-DAISY.mid \
   out/bundle/ 2>/dev/null || true
cp source/01_Lobe_den_Herren.pdf out/bundle/Quelle_01_Lobe_den_Herren.pdf
cp source/Lobe-den-Herren-OMR.mscz out/bundle/OMR-Vorlage.mscz
if [ -f report/BERICHT.md ]; then cp report/BERICHT.md out/bundle/; fi
cd out/bundle
sha256sum * > MANIFEST-SHA256.txt
ls -la
cat MANIFEST-SHA256.txt
