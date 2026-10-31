#!/usr/bin/env python3
"""MakeBraille (dzb lesen) — MusicXML/CapX nach Musikbraille wandeln.

Das Passwort kommt aus dem Hermes-Vault: der Eintrag wird anhand der Origin
(https://makebraille.dzblesen.de) gefunden und hier im Prozess aufgeloest,
ohne je in eine Ausgabe oder in ein Chatprotokoll zu geraten.

Aufrufe (ueber scripts/run.sh, das die Hermes-Laufzeit findet):

    run.sh check                      # Login testen, Ergebnis melden
    run.sh dump                       # Startseite nach dem Login als HTML sichern
    run.sh dump --url <url>           # beliebige Seite nach dem Login sichern
    run.sh convert datei.musicxml     # konvertieren (Ausgabe nach --out)
    run.sh batch 'stuecke/*.musicxml' # Stapel

Optionen:
    --handle vault_xxxxxxxxxxxx   bestimmten Vault-Eintrag nehmen
    --out DIR                     Zielordner (Standard: ./out)
    --user NAME --password-file F ohne Vault arbeiten (Datei mit dem Passwort)

Nur Standardbibliothek — laeuft mit der Hermes-Python-Laufzeit.
"""

from __future__ import annotations

import argparse
import getpass
import glob
import http.cookiejar
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path

# --- Hermes-Laufzeit (Vault-Zugriff) ---------------------------------------
REPO = os.environ.get("HERMES_REPO", os.path.expanduser("~/.hermes/hermes-agent"))
HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
if os.path.isdir(REPO) and REPO not in sys.path:
    sys.path.insert(0, REPO)
os.environ.setdefault("HERMES_HOME", HERMES_HOME)
try:  # richtet den Paketpfad der Hermes-Installation ein
    import hermes_bootstrap  # noqa: F401
except Exception:  # pragma: no cover — nur noetig, wenn der Vault benutzt wird
    pass

# --- Dienst -----------------------------------------------------------------
BASE = "https://makebraille.dzblesen.de"
LOGIN_PATH = "/MakeBraille"
ORIGIN = "https://makebraille.dzblesen.de"
DEFAULT_LABEL = "dzb lesen MakeBraille"
USER_AGENT = "Hermes-Agent MakeBraille-Client/1.0"
MAX_LOGIN_LEN = 30
MAX_PASSWORD_LEN = 30


class MakeBrailleError(RuntimeError):
    pass


# --- Zugangsdaten -----------------------------------------------------------
def credentials_from_vault(handle: str | None = None) -> tuple[str, str, str]:
    """(Benutzer, Passwort, Quelle) aus dem Hermes-Vault."""
    try:
        from agent.vault_store import get_vault_store, normalize_origin
    except Exception as exc:  # pragma: no cover
        raise MakeBrailleError(
            f"Vault nicht erreichbar ({exc}). Mit --user/--password-file arbeiten."
        ) from exc

    store = get_vault_store()
    wanted = normalize_origin(ORIGIN)
    items = store.list_items()
    if handle:
        cand = [i for i in items if i.id == handle]
    else:
        cand = [i for i in items if i.kind == "login" and normalize_origin(i.origin or "") == wanted]
    if not cand:
        raise MakeBrailleError(
            f"Kein Vault-Login fuer {wanted}. Anlegen mit:\n"
            f"  printf 'login\\n{DEFAULT_LABEL}\\n{ORIGIN}\\nusername\\n<BENUTZER>\\n' | hermes vault add"
        )
    item = cand[0]
    secret = store.resolve_secret(item.id)
    user = str(secret.get("identifier") or item.identifier or "")
    password = str(secret.get("password") or "")
    if not user or not password:
        raise MakeBrailleError(f"Vault-Eintrag {item.id} hat keine vollstaendigen Zugangsdaten.")
    return user, password, f"vault ({item.id}, {item.label})"


def credentials_from_args(args) -> tuple[str, str, str]:
    if args.user or args.password_file:
        if not args.user:
            raise MakeBrailleError("--user fehlt.")
        if not args.password_file:
            pw = getpass.getpass("Passwort (wird nicht angezeigt): ")
        else:
            pw = Path(args.password_file).read_text(encoding="utf-8").strip()
        return args.user, pw, "Argumente/Datei"
    return credentials_from_vault(args.handle)


# --- HTTP-Sitzung -----------------------------------------------------------
class Session:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            NoRedirect(),
        )
        self.opener.addheaders = [("User-Agent", USER_AGENT)]

    def request(self, url: str, data: bytes | None = None, headers: dict | None = None):
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with self.opener.open(req, timeout=120) as resp:
                return resp.geturl(), resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            return url, exc.headers, exc.read()

    def get(self, url: str):
        return self.request(url)

    def post(self, url: str, fields: dict[str, str]):
        return self.request(url, urllib.parse.urlencode(fields).encode("utf-8"),
                            {"Content-Type": "application/x-www-form-urlencoded"})

    def post_multipart(self, url: str, fields: dict[str, str], files: dict[str, tuple[str, bytes]]):
        boundary = "----hermes" + uuid.uuid4().hex
        body = io.BytesIO()
        for name, value in fields.items():
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.write(str(value).encode("utf-8") + b"\r\n")
        for name, (filename, payload) in files.items():
            body.write(f"--{boundary}\r\n".encode())
            body.write(
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            )
            body.write(b"Content-Type: application/octet-stream\r\n\r\n")
            body.write(payload + b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())
        return self.request(url, body.getvalue(),
                            {"Content-Type": f"multipart/form-data; boundary={boundary}"})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects nicht automatisch folgen — die Antwort selbst auswerten."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


# --- Seitenanalyse ----------------------------------------------------------
class FormParser(HTMLParser):
    """Sammelt Formulare samt Feldern, damit nach dem Login nichts geraten werden muss."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.forms: list[dict] = []
        self._current: dict | None = None
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "form":
            self._current = {"action": a.get("action", ""), "method": (a.get("method") or "get").lower(),
                             "enctype": a.get("enctype", ""), "fields": [], "files": [], "submits": []}
        elif tag in ("input", "select", "textarea", "button") and self._current is not None:
            name = a.get("name")
            if not name:
                return
            itype = (a.get("type") or ("submit" if tag == "button" else "text")).lower()
            entry = {"name": name, "type": itype, "value": a.get("value", "")}
            if itype == "file":
                self._current["files"].append(entry)
            elif itype in ("submit", "button", "image"):
                self._current["submits"].append(entry)
                self._current["fields"].append(entry)
            else:
                self._current["fields"].append(entry)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "form" and self._current is not None:
            self.forms.append(self._current)
            self._current = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse(html: bytes) -> FormParser:
    p = FormParser()
    p.feed(html.decode("utf-8", "replace"))
    return p


def looks_like_login(html: bytes) -> bool:
    return b'name="passwd"' in html or b"MakeBraille &#8212; Login" in html


# --- Ablauf -----------------------------------------------------------------
def do_login(sess: Session, user: str, password: str) -> bytes:
    if len(user) > MAX_LOGIN_LEN or len(password) > MAX_PASSWORD_LEN:
        raise MakeBrailleError(
            f"Benutzer/Passwort laenger als {MAX_LOGIN_LEN} Zeichen — das Formular lehnt das ab."
        )
    _, headers, body = sess.post(
        BASE + LOGIN_PATH,
        {"login": user, "passwd": password, "mode": "server_login"},
    )
    if looks_like_login(body):
        raise MakeBrailleError("Login abgelehnt — Zugangsdaten falsch?")
    return body


def cmd_check(args) -> int:
    user, password, source = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    body = do_login(sess, user, password)
    p = parse(body)
    print(f"Login ok ({source}).")
    print(f"Seitentitel: {p.title.strip() or '(ohne Titel)'}")
    print(f"Formulare: {len(p.forms)}")
    for i, form in enumerate(p.forms, 1):
        files = ", ".join(f["name"] for f in form["files"]) or "-"
        print(f"  [{i}] action={form['action']!r} method={form['method']} enctype={form['enctype']!r}")
        print(f"      Felder: {', '.join(f['name'] for f in form['fields']) or '-'}")
        print(f"      Datei: {files}")
    return 0


def cmd_dump(args) -> int:
    user, password, _ = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    body = do_login(sess, user, password)
    url = args.url or None
    if url:
        _, _, body = sess.get(urllib.parse.urljoin(BASE + "/", url))
    out = Path(args.out) / (args.name or "seite.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"gespeichert: {out} ({len(body)} Byte)")
    return 0


def cmd_convert(args) -> int:
    """Datei(en) hochladen und die Braille-Antwort sichern.

    Der Upload nutzt das erste Formular der Startseite mit einem Dateifeld; alle
    uebrigen Felder werden mit ihren Vorgabewerten mitgeschickt, Submit-Felder
    mit dem ersten Submit-Knopf.
    """
    user, password, _ = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    home = do_login(sess, user, password)
    p = parse(home)
    target = next((f for f in p.forms if f["files"]), None)
    if target is None:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out) / "startseite.html").write_bytes(home)
        raise MakeBrailleError(
            "Nach dem Login kein Formular mit Dateifeld gefunden — Startseite in "
            f"{args.out}/startseite.html gesichert; Formular unbekannt."
        )
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rc = 0
    for path in args.files:
        src = Path(path)
        data = src.read_bytes()
        fields = {f["name"]: f["value"] for f in target["fields"] if f["type"] not in ("file", "submit")}
        if target["submits"]:
            fields[target["submits"][0]["name"]] = target["submits"][0]["value"]
        url = target["action"] or (BASE + LOGIN_PATH)
        url = urllib.parse.urljoin(BASE + "/", url)
        filefield = target["files"][0]["name"]
        _, headers, body = sess.post_multipart(url, fields, {filefield: (src.name, data)})
        ctype = (headers.get("Content-Type") or "").lower()
        if "html" in ctype or b"<!DOCTYPE html" in body[:200].lower():
            dest = outdir / (src.stem + ".antwort.html")
            dest.write_bytes(body)
            print(f"{src.name}: HTML-Antwort gesichert -> {dest} ({len(body)} Byte)")
            rc = 1
        else:
            name = _filename_from_headers(headers) or (src.stem + ".brf")
            dest = outdir / name
            dest.write_bytes(body)
            print(f"{src.name}: Braille gespeichert -> {dest} ({len(body)} Byte)")
    return rc


def _filename_from_headers(headers) -> str | None:
    disp = headers.get("Content-Disposition") or ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disp)
    return Path(m.group(1)).name if m else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="makebraille", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--handle", help="Vault-Eintrag (Standard: der zur Origin passende)")
    ap.add_argument("--out", default="out", help="Zielordner (Standard: ./out)")
    ap.add_argument("--user")
    ap.add_argument("--password-file")
    subs = ap.add_subparsers(dest="cmd", required=True)

    subs.add_parser("check", help="Login testen")
    d = subs.add_parser("dump", help="Seite nach dem Login sichern")
    d.add_argument("--url")
    d.add_argument("--name")
    c = subs.add_parser("convert", help="Datei(en) konvertieren")
    c.add_argument("files", nargs="+")
    b = subs.add_parser("batch", help="Stapel (Glob-Muster)")
    b.add_argument("patterns", nargs="+")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "check":
            return cmd_check(args)
        if args.cmd == "dump":
            return cmd_dump(args)
        if args.cmd == "convert":
            return cmd_convert(args)
        if args.cmd == "batch":
            files = [f for pat in args.patterns for f in sorted(glob.glob(pat))]
            if not files:
                print("keine Dateien gefunden", file=sys.stderr)
                return 2
            args.files = files
            return cmd_convert(args)
    except MakeBrailleError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
