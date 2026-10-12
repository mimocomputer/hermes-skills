#!/bin/bash
# Build Audiveris 5.11.0 from source (once) and run headless OMR over one or more PDFs.
# Produces a CROSS-CHECK draft only. When the user has supplied his own OMR/MusicXML
# export, that file is the base to correct and this draft is a second opinion.
#
# Usage: run_audiveris_omr.sh <project-dir> <pdf-in-source> [<project-dir> <pdf> ...]
set -uo pipefail

AUD_SRC=/home/ubuntu/.local/opt/audiveris-src
AUD_ROOT=/home/ubuntu/.local/opt/audiveris-5.11.0
AUD_BIN="$AUD_ROOT/app-5.11.0/bin/Audiveris"
JDK=/usr/lib/jvm/java-25-openjdk-arm64   # Audiveris 5.11 declares source/target 25
TESS="$HOME/.config/AudiverisLtd/audiveris/tessdata"

if [ ! -x "$AUD_BIN" ]; then
  echo "== building Audiveris 5.11.0 from source"
  mkdir -p /home/ubuntu/.local/opt
  [ -d "$AUD_SRC/.git" ] || git clone --depth 1 --branch 5.11.0 https://github.com/Audiveris/audiveris.git "$AUD_SRC"
  ( cd "$AUD_SRC" && JAVA_HOME="$JDK" PATH="$JDK/bin:$PATH" ./gradlew --no-daemon build ) || exit 1
  mkdir -p "$AUD_ROOT" && tar -xf "$AUD_SRC/app/build/distributions/app-5.11.0.tar" -C "$AUD_ROOT"
fi

mkdir -p "$TESS"
[ -s "$TESS/eng.traineddata" ] || cp /usr/share/tesseract-ocr/5/tessdata/eng.traineddata "$TESS/" 2>/dev/null || \
  curl -sSL https://raw.githubusercontent.com/tesseract-ocr/tessdata/4.1.0/eng.traineddata -o "$TESS/eng.traineddata"

while [ $# -ge 2 ]; do
  dir=$1; pdf=$2; shift 2
  echo "===== OMR $dir : $pdf ====="
  date -u +%H:%M:%S
  TESSDATA_PREFIX="$TESS" JAVA_HOME="$JDK" PATH="$JDK/bin:$PATH" \
    "$AUD_BIN" -batch -force -save -export -output "$dir/work/omr" -- "$dir/source/$pdf" \
    > "$dir/work/omr.log" 2>&1
  echo "exit=$?"
  date -u +%H:%M:%S
  ls -la "$dir/work/omr" 2>/dev/null
  # Sanity: an export that explodes the choir into junk-named parts is a cross-check only.
  python3 - "$dir/work/omr/${pdf%.pdf}.mxl" <<'PY'
import re, sys, zipfile
p = sys.argv[1]
try:
    z = zipfile.ZipFile(p)
    root = [n for n in z.namelist() if n.endswith('.xml') and 'META-INF' not in n][0]
    x = z.read(root).decode('utf-8', 'replace')
except Exception as e:
    print('MXL UNREADABLE:', e); raise SystemExit
print('parts  :', re.findall(r'<part-name>([^<]*)</part-name>', x))
print('measures:', len(re.findall(r'<measure ', x)), ' notes:', len(re.findall(r'<note[ >]', x)),
      ' lyrics:', len(re.findall(r'<lyric', x)))
PY
done
echo OMR_BATCH_DONE
