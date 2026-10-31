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

    def request(self, url: str, data: bytes | None = None, headers: dict | None = None,
                _depth: int = 0):
        """Eine Anfrage, Redirects werden manuell nachgezogen (max. 5).

        Rueckgabe: (endgueltige URL, Status, Header, Rumpf).
        """
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with self.opener.open(req, timeout=180) as resp:
                status, hdrs, body, final = resp.status, resp.headers, resp.read(), resp.geturl()
        except urllib.error.HTTPError as exc:
            status, hdrs, body, final = exc.code, exc.headers, exc.read(), url
        if 300 <= status < 400 and _depth < 5:
            loc = hdrs.get("Location")
            if loc:
                target = urllib.parse.urljoin(final, loc)
                if status in (307, 308) and data is not None:
                    return self.request(target, data, headers, _depth + 1)
                return self.request(target, None, None, _depth + 1)
        return final, status, hdrs, body

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
        self._select: dict | None = None
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "form":
            self._current = {"action": a.get("action", ""), "method": (a.get("method") or "get").lower(),
                             "enctype": a.get("enctype", ""), "fields": [], "files": [], "submits": []}
        elif tag == "select" and self._current is not None and a.get("name"):
            self._select = {"name": a["name"], "type": "select", "value": "", "options": []}
            self._current["fields"].append(self._select)
        elif tag == "option" and self._select is not None:
            value = a.get("value", "")
            self._select["options"].append(value)
            if "selected" in a or self._select["value"] == "":
                self._select["value"] = value
        elif tag in ("input", "textarea", "button") and self._current is not None:
            name = a.get("name")
            if not name:
                return
            itype = (a.get("type") or ("submit" if tag == "button" else "text")).lower()
            entry = {"name": name, "type": itype, "value": a.get("value", ""),
                     "checked": "checked" in a, "disabled": "disabled" in a}
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
        elif tag == "select":
            self._select = None
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
    _, status, _, body = sess.post(
        BASE + LOGIN_PATH,
        {"login": user, "passwd": password, "mode": "server_login"},
    )
    if not body:
        raise MakeBrailleError(f"Login: leere Antwort (HTTP {status}).")
    if looks_like_login(body):
        raise MakeBrailleError("Login abgelehnt — Zugangsdaten falsch?")
    return body


def _describe_forms(p: FormParser) -> None:
    print(f"Seitentitel: {p.title.strip() or '(ohne Titel)'}")
    print(f"Formulare: {len(p.forms)}")
    for i, form in enumerate(p.forms, 1):
        print(f"  [{i}] action={form['action']!r} method={form['method']} enctype={form['enctype']!r}")
        for f in form["fields"]:
            if f["type"] in ("submit", "button", "image"):
                continue
            extra = ""
            if f["type"] == "select":
                extra = f"  Optionen: {', '.join(f.get('options', []))}"
            elif f["type"] in ("radio", "checkbox"):
                extra = "  [angehakt]" if f.get("checked") else ""
            print(f"      {f['name']} ({f['type']}) = {f['value']!r}{extra}")
        print(f"      Dateifelder: {', '.join(f['name'] for f in form['files']) or '-'}")
        if form["submits"]:
            print("      Buttons: " + ", ".join(f"{s['name']}={s['value']}" for s in form["submits"]))


def _upload_form(home: bytes) -> dict | None:
    p = parse(home)
    return next((f for f in p.forms if f["files"]), None)


def _form_fields(form: dict, mode: str | None = None, profile: str | None = None) -> dict[str, str]:
    """Alle nicht-Button-Felder mit ihren Vorgabewerten; Select-Werte inklusive."""
    fields: dict[str, str] = {}
    for f in form["fields"]:
        if f["type"] in ("file", "submit", "button", "image") or f.get("disabled"):
            continue
        if f["type"] in ("radio", "checkbox") and not f.get("checked"):
            continue  # nicht angehakte Wahlfelder werden nicht mitgeschickt
        fields[f["name"]] = f["value"]
    if profile:
        fields["uprofile_selector"] = profile
    if mode:
        fields["mode"] = mode
    return fields


def cmd_check(args) -> int:
    user, password, source = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    body = do_login(sess, user, password)
    print(f"Login ok ({source}).")
    _describe_forms(parse(body))
    return 0


def cmd_dump(args) -> int:
    user, password, _ = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    body = do_login(sess, user, password)
    page = "seite.html"
    if args.mode:
        form = _upload_form(body) or (parse(body).forms or [None])[0]
        if form is None:
            raise MakeBrailleError("Kein Formular auf der Startseite gefunden.")
        url = urllib.parse.urljoin(BASE + "/", form["action"] or LOGIN_PATH)
        fields = _form_fields(form, mode=args.mode, profile=args.profile)
        _, status, _, body = sess.post_multipart(url, fields, {})
        page = f"seite-{args.mode}.html"
        print(f"POST {url} (mode={args.mode}" + (f", profile={args.profile}" if args.profile else "") + ")")
    elif args.url:
        _, status, _, body = sess.get(urllib.parse.urljoin(BASE + "/", args.url))
    name = args.name or page
    out = Path(args.out) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"gespeichert: {out} ({len(body)} Byte)")
    return 0


def cmd_config(args) -> int:
    """Konfigurationsseite lesen; optional als neues Profil speichern.

    Ohne --save wird nur berichtet (aktuelles Profil, Empfängeradresse und die
    wichtigsten Einstellungen). Mit --save wird die Seite mit den vorhandenen
    Werten abgeschickt und dabei Profilname (--name) und/oder Adresse (--email)
    ersetzt — so laesst sich ein Profil klonen, ohne die Einstellungen von Hand
    zu setzen.
    """
    user, password, _ = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    home = do_login(sess, user, password)
    form = _upload_form(home)
    if form is None:
        raise MakeBrailleError("Startseiten-Formular nicht gefunden.")
    url = urllib.parse.urljoin(BASE + "/", form["action"] or LOGIN_PATH)
    _, _, _, page = sess.post_multipart(url, _form_fields(form, mode="configuration"), {})
    p = parse(page)
    cform = next((f for f in p.forms if any(x["name"] == "email" for x in f["fields"])), None)
    if cform is None:
        out = Path(args.out) / "konfiguration.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(page)
        raise MakeBrailleError(f"Konfigurationsformular nicht gefunden — Seite in {out} gesichert.")

    prof = next((f for f in cform["fields"] if f["name"] == "uprofile_intrabitor"), None)
    current = {f["name"]: f["value"] for f in cform["fields"]
               if f["type"] not in ("file", "submit", "button", "image")}
    sel = next((f for f in cform["fields"] if f["name"] == "uprofile_selector"), None)
    print(f"Aktuelles Profil: {current.get('uprofile_intrabitor', '?')}")
    print(f"Empfängeradresse: {current.get('email', '?')}")
    for key in ("makebraille_out_format", "country", "user_profile", "text_format", "division", "merge_parts"):
        val = next((f["value"] for f in cform["fields"]
                    if f["name"] == key and f.get("checked")), None)
        print(f"  {key}: {val}")
    if sel:
        print("  Profile: " + ", ".join(sel.get("options", [])))

    if not args.save:
        print("(nur gelesen — mit --save --name/--email wird ein Profil gespeichert)")
        return 0

    fields = dict(current)
    if args.name:
        fields["uprofile_intrabitor"] = args.name
    if args.email:
        fields["email"] = args.email
    fields["mode"] = "save_configuration"
    _, status, _, page = sess.post_multipart(url, fields, {})
    out = Path(args.out) / "konfiguration-nach-save.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(page)
    p2 = parse(page)
    sel2 = next((f for f in p2.forms[0]["fields"] if f["name"] == "uprofile_selector"), None) if p2.forms else None
    prof2 = next((f for f in p2.forms[0]["fields"] if f["name"] == "uprofile_intrabitor"), None) if p2.forms else None
    print(f"gespeichert: HTTP {status}; Profil jetzt: {prof2['value'] if prof2 else '?'}")
    if sel2:
        print("  Profile: " + ", ".join(sel2.get("options", [])))
    print(f"  Seite: {out}")
    return 0


def _summarize_html(body: bytes) -> str:
    """Kurzbeschreibung einer HTML-Antwort (Titel + Links auf Dateien)."""
    text = body.decode("utf-8", "replace")
    p = parse(body)
    lines = [f"Titel: {p.title.strip() or '(ohne Titel)'}"]
    links = re.findall(r'href=["\']([^"\']+)["\']', text)
    interesting = [l for l in links if re.search(r"\.(brf|txt|zip|xml|mxl|musicxml|capx|pdf)$", l, re.I)
                   or "download" in l.lower()]
    if interesting:
        lines.append("Links: " + ", ".join(dict.fromkeys(interesting)))
    return " | ".join(lines)


def _selected_profile(page: bytes) -> str | None:
    """Aktiv gewaehltes Profil (``<option ... selected>``) aus einer Seite."""
    for form in parse(page).forms:
        for f in form["fields"]:
            if f["name"] == "uprofile_selector":
                return f["value"] or None
    return None


_STATUS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("still being converted", "angenommen — Konvertierung laeuft, Ergebnis kommt per E-Mail"),
    ("converted", "Antwort nennt eine fertige Konvertierung"),
    ("error", "Antwort enthaelt 'error'"),
    ("fehler", "Antwort enthaelt 'Fehler'"),
    ("problem", "Antwort enthaelt 'problem'"),
    ("not valid", "Antwort meldet eine ungueltige Datei"),
    ("please wait", "angenommen — bitte warten"),
)


def _status_line(body: bytes) -> str:
    """Die dynamische Statuszeile der Antwort (z. B. 'still being converted')."""
    text = body.decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    for needle, message in _STATUS_PATTERNS:
        if needle in text.lower():
            return message
    m = re.search(r"Main page (.{0,160}?) Hints", text)
    return (m.group(1).strip() if m else "")[:160]


def cmd_convert(args) -> int:
    """Datei(en) hochladen und die Braille-Antwort sichern.

    Der Upload benutzt das Formular der Startseite mit dem Dateifeld; alle
    uebrigen Felder gehen mit ihren Vorgabewerten mit, der Submit-Knopf mit dem
    Wert von --mode (Standard: create). Mit --profile wird zuerst ausdruecklich
    umgeschaltet (mode=switch_uprofile) und das Ergebnis geprueft — ein
    ``uprofile_selector`` im Upload-POST allein wechselt das Profil nicht
    zuverlaessig. Die Antwort wird auf die Statuszeile geprueft ("Your file is
    still being converted" = angenommen); die Datei selbst kommt per E-Mail ans
    Profil.
    """
    user, password, _ = credentials_from_args(args)
    sess = Session()
    sess.get(BASE + LOGIN_PATH)
    home = do_login(sess, user, password)
    target = _upload_form(home)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    if target is None:
        (outdir / "startseite.html").write_bytes(home)
        raise MakeBrailleError(
            "Nach dem Login kein Formular mit Dateifeld gefunden — Startseite in "
            f"{outdir}/startseite.html gesichert."
        )
    fields = _form_fields(target, mode=args.mode)
    url = urllib.parse.urljoin(BASE + "/", target["action"] or LOGIN_PATH)
    if args.profile:
        switch = _form_fields(target, mode="switch_uprofile", profile=args.profile)
        _, status, _, page = sess.post_multipart(url, switch, {})
        active = _selected_profile(page)
        if active and active != args.profile:
            raise MakeBrailleError(
                f"Profilwechsel fehlgeschlagen: aktiv bleibt {active!r}, nicht {args.profile!r}."
            )
        after = _upload_form(page)
        if after is None:
            (outdir / "profilwechsel.html").write_bytes(page)
            raise MakeBrailleError("Nach dem Profilwechsel kein Upload-Formular gefunden "
                                   f"(Seite in {outdir}/profilwechsel.html).")
        target, fields = after, _form_fields(after, mode=args.mode)
        print(f"Profil {args.profile!r} aktiv (HTTP {status}); Upload mit diesem Profil.")
    filefield = target["files"][0]["name"]
    print(f"Upload nach {url} mit {filefield!r}, Felder: {', '.join(fields)}")
    rc = 0
    for path in args.files:
        src = Path(path)
        data = src.read_bytes()
        _, status, headers, body = sess.post_multipart(url, fields, {filefield: (src.name, data)})
        ctype = (headers.get("Content-Type") or "").lower()
        print(f"   HTTP {status}, {ctype or 'ohne Content-Type'}, {len(body)} Byte")
        if body and ("html" in ctype or body[:200].lower().lstrip().startswith(b"<!doctype html")):
            dest = outdir / (src.stem + ".antwort.html")
            dest.write_bytes(body)
            print(f"{src.name}: HTML-Antwort -> {dest} ({len(body)} Byte)")
            print(f"   {_summarize_html(body)}")
            print(f"   Status: {_status_line(body)}")
            rc = max(rc, 1)
        elif body:
            name = _filename_from_headers(headers) or (src.stem + ".brf")
            dest = outdir / name
            dest.write_bytes(body)
            print(f"{src.name}: Braille gespeichert -> {dest} ({len(body)} Byte, {ctype or 'ohne Typ'})")
        else:
            print(f"{src.name}: leere Antwort (HTTP {status}) — keine Bestaetigung, Upload wiederholen.")
            rc = max(rc, 2)
    return rc


def _filename_from_headers(headers) -> str | None:
    disp = headers.get("Content-Disposition") or ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disp)
    return Path(m.group(1)).name if m else None


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--handle", default=argparse.SUPPRESS,
                        help="Vault-Eintrag (Standard: der zur Origin passende)")
    common.add_argument("--out", default=argparse.SUPPRESS, help="Zielordner (Standard: ./out)")
    common.add_argument("--user", default=argparse.SUPPRESS)
    common.add_argument("--password-file", default=argparse.SUPPRESS)

    ap = argparse.ArgumentParser(prog="makebraille", description=__doc__,
                                 parents=[common],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = ap.add_subparsers(dest="cmd", required=True)

    subs.add_parser("check", help="Login testen", parents=[common])
    d = subs.add_parser("dump", help="Seite nach dem Login sichern", parents=[common])
    d.add_argument("--url", help="diese Seite laden statt der Startseite")
    d.add_argument("--mode", help="Startseiten-Formular mit diesem mode-Wert abschicken")
    d.add_argument("--profile", help="dabei uprofile_selector setzen (z. B. Chor)")
    d.add_argument("--name")
    c = subs.add_parser("convert", help="Datei(en) konvertieren", parents=[common])
    c.add_argument("files", nargs="+")
    c.add_argument("--mode", default="create", help="Submit-Wert des Formulars (Standard: create)")
    c.add_argument("--profile", help="uprofile_selector, z. B. Chor, Orgel, Orgel_Englisch")
    cf = subs.add_parser("config", help="Konfigurationsprofil ansehen/ablegen", parents=[common])
    cf.add_argument("--name", help="Profilname beim Speichern")
    cf.add_argument("--email", help="Empfängeradresse beim Speichern")
    cf.add_argument("--save", action="store_true", help="Seite abschicken (neues Profil/Änderung)")
    b = subs.add_parser("batch", help="Stapel (Glob-Muster)", parents=[common])
    b.add_argument("patterns", nargs="+")
    b.add_argument("--mode", default="create")
    b.add_argument("--profile")

    args = ap.parse_args(argv)
    # Optionen duerfen vor oder nach dem Unterbefehl stehen; SUPPRESS haelt die
    # Vorgabe des Hauptparsers am Leben.
    for name, default in (("handle", None), ("out", "out"), ("user", None), ("password_file", None)):
        if not hasattr(args, name):
            setattr(args, name, default)
    try:
        if args.cmd == "check":
            return cmd_check(args)
        if args.cmd == "dump":
            return cmd_dump(args)
        if args.cmd == "convert":
            return cmd_convert(args)
        if args.cmd == "config":
            return cmd_config(args)
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
