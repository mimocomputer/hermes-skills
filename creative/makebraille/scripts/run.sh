#!/bin/sh
# Startet den MakeBraille-Client in der Hermes-Python-Laufzeit (Zugriff auf den Vault).
#
#   run.sh check
#   run.sh dump --url /MakeBraille
#   run.sh convert werk.musicxml --out out
#   run.sh batch "musicxml/*.musicxml"
#
# Andere Laufzeit erzwingen:  HERMES_PY=/pfad/python3 run.sh …
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${HERMES_PY:-}" ]; then
    py=$HERMES_PY
else
    py=$(ls -d "$HOME"/.hermes/tools/python-*/bin/python3 2>/dev/null | head -n 1 || true)
fi
if [ -z "${py:-}" ] || [ ! -x "$py" ]; then
    echo "run.sh: Hermes-Python nicht gefunden (HERMES_PY setzen)." >&2
    exit 1
fi

exec "$py" "$here/makebraille.py" "$@"
