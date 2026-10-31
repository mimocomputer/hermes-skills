#!/usr/bin/env python3
"""Legt den MakeBraille-Zugang aus einer Datei verschluesselt im Hermes-Vault ab.

Die Datei enthaelt den Benutzernamen und das Passwort, z. B.

    Benutzer: jdreykorn
    Passwort: geheimespasswort

oder einfach zwei Zeilen (1 = Benutzer, 2 = Passwort). Das Passwort wird nie
ausgegeben: es geht ueber eine Pipe in `hermes vault add`, wo nur die verdeckte
(getpass-)Abfrage es liest. Danach wird die Datei geloescht (--keep-file laesst
sie stehen).

    ./vault_add_makebraille.py /pfad/zugang.txt
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

LABEL = "dzb lesen MakeBraille"
ORIGIN = "https://makebraille.dzblesen.de"
LOGIN_KEYS = ("benutzer", "benutzername", "username", "login", "kennung", "user")
PASS_KEYS = ("passwort", "password")


def parse(path: Path) -> tuple[str, str]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    user = pw = None
    for ln in lines:
        low = ln.lower()
        if any(re.match(rf"^{k}\s*:", low) for k in LOGIN_KEYS):
            user = ln.split(":", 1)[1].strip()
        elif any(re.match(rf"^{k}\s*:", low) for k in PASS_KEYS):
            pw = ln.split(":", 1)[1].strip()
    if pw is None:
        rest = [ln for ln in lines if ln != user]
        if user is None and len(rest) >= 2:
            user, pw = rest[0], rest[1]
        elif len(rest) == 1:
            pw = rest[0]
    if not user or not pw:
        raise SystemExit("Datei muss Benutzer und Passwort enthalten (Zeilen oder 'Benutzer:'/'Passwort:').")
    return user, pw


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1])
    if not src.is_file():
        raise SystemExit(f"Datei nicht gefunden: {src}")
    keep = "--keep-file" in sys.argv
    user, pw = parse(src)

    stdin = f"login\n{LABEL}\n{ORIGIN}\nusername\n{user}\n{pw}\n\n"
    done = subprocess.run(["hermes", "vault", "add"], input=stdin.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = done.stdout.decode("utf-8", "replace")
    ok = done.returncode == 0 and "Stored." in out
    for line in out.splitlines():
        if line.startswith(("Stored.", "Label", "Origin")):
            print(line)
    if not ok:
        print(out.strip()[-500:], file=sys.stderr)
        return 1
    print(f"Im Vault abgelegt (Label {LABEL!r}, Origin {ORIGIN}), Kennung {user!r}.")
    if not keep:
        src.unlink()
        print(f"Datei geloescht: {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
