---
name: makebraille
description: "Use when converting MusicXML or CapX scores to music Braille via dzb lesen's MakeBraille service. Vault-backed login, batch conversion, verified end-to-end plumbing."
version: 0.1.0
author: Hermes Agent + Julian
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [braille, music, accessibility, musicxml, capx, dzb-lesen, vault, daisy]
    related_skills: [musicxml-engraving-accessibility, vector-score-to-musicxml]
---

# MakeBraille (dzb lesen) — MusicXML nach Musikbraille

Konvertiert MusicXML (und CapX) über den Online-Dienst von dzb lesen in Musikbraille:
**https://makebraille.dzblesen.de/MakeBraille** — Login nötig, Benutzername und Passwort
jeweils **max. 30 Zeichen**. Nutzungsbedingungen: nur privat/nicht-kommerziell,
gemeinfreie Werke sowie rechtmäßig genutzte urheberrechtlich geschützte Werke und eigene
Sätze; dzb lesen wertet die Nutzung aus und freut sich über Rückmeldung
(makebraille-support@dzblesen.de). Details siehe `references/makebraille-service.md`.

## Vorgehen

Für wiederkehrende Konvertierungen einen **Client + Skill** bauen und pflegen, nicht den Browser
bedienen: der Login wandert einmal in den Vault, danach läuft alles headless (auch aus Cron- und
Webhook-Sitzungen). Der Client gehört an den Vault, nicht an ein abgetipptes Passwort — jede
weitere Konvertierung soll ohne Zutun und ohne Interaktion auskommen. Reicht das Webformular
nicht, ist der Client die Stelle zum Nachziehen (`scripts/makebraille.py`), nicht ein zweiter
Ad-hoc-Aufruf.

## Zugangsdaten

Der Login liegt im Hermes-Credential-Vault, gebunden an die Origin
`https://makebraille.dzblesen.de` (Schema + Host, der Pfad zählt nicht). Anlegen — in einer
interaktiven Sitzung fragt `hermes vault add` das Passwort verdeckt ab:

```bash
printf 'login\ndzb lesen MakeBraille\nhttps://makebraille.dzblesen.de\nusername\n<BENUTZER>\n' | hermes vault add
```

Aus einer Datei (Zeile 1 Benutzer, Zeile 2 Passwort, oder `Benutzer:`/`Passwort:`) — legt den
Eintrag an und löscht die Datei danach:

```bash
scripts/vault_add_makebraille.py /pfad/zugang.txt
```

**Nie** ein Passwort im Chat annehmen: Gateway-Sitzungen (Matrix, Telegram, …) haben keinen
verdeckten Eingabekanal — alles Getippte landet im Modellkontext, in der Session-DB und auf dem
Plattformserver. Nur interaktive Oberflächen (CLI/TUI, Desktop-App) können Passwörter maskiert
einfangen. Hintergrund: Skill `hermes-agent`, `references/security-privacy.md`.

## Benutzung

`scripts/run.sh` startet den Client in der Hermes-Python-Laufzeit, damit er den Vault lesen kann
(das Passwort wird im Prozess aufgelöst und nie ausgegeben; `HERMES_PY=/pfad/python3` erzwingt
eine andere Laufzeit):

```bash
scripts/run.sh check                       # Login testen, Formulare der Startseite listen
scripts/run.sh dump --url /MakeBraille     # Seite nach dem Login als HTML sichern
scripts/run.sh convert werk.musicxml --out out
scripts/run.sh batch 'musicxml/*.musicxml' --out out
```

Ohne Vault (andere Umgebung): `--user <name> --password-file <datei>`. Passwörter **nie** als
Kommandozeilenargument übergeben — sie stehen sonst in der Prozessliste.

## Stand und Grenzen

* **Geprüft:** Vault-Anlage über beide Wege, Vault-Auflösung, HTTP-Sitzung (Cookies), Login-POST
  auf `/MakeBraille` mit `login`/`passwd`/`mode=server_login` und die Fehlererkennung — eine
  falsche Kennung liefert wieder die Login-Seite, der Client meldet „Login abgelehnt".
* **Noch zu bestätigen:** der Upload-Schritt. Er ist generisch gebaut (erstes Formular mit
  Dateifeld, versteckte Felder werden übernommen) und wurde noch **nicht** gegen die echte
  Seite nach dem Login geprüft. Erster Schritt mit echten Daten daher: `run.sh dump`, Formular
  ansehen, dann `convert`; bei abweichendem Formular `cmd_convert` in `scripts/makebraille.py`
  nachziehen.
* **Kein Login = keine Auskunft:** Der Dienst beantwortet jeden Aufruf ohne gültige Sitzung mit
  HTTP 200 und der Login-Seite — deshalb prüft der Client den Inhalt, nicht den Statuscode.

## Stolpersteine

* Origin-Bindung ist exakt: ein für `dzblesen.de` gespeicherter Login gilt nicht für
  `makebraille.dzblesen.de` und umgekehrt.
* `https://dzblesen.de/makebraille` und `https://www.dzblesen.de/makebraille` leiten per 301 auf
  `https://makebraille.dzblesen.de/MakeBraille` weiter — immer die Endadresse als Origin nehmen.
* Der Vault-Eintrag gehört ins Standardprofil; in Cron-/Webhook-Sitzungen funktioniert er
  weiterhin (lokale Vault-Einträge brauchen keinen Prompt), in fremden Profilen nicht.
* Neue Unterbefehle im Client brauchen `parents=[common]`, sonst lehnt argparse die globalen
  Optionen (`--out`, `--handle`, `--user`, `--password-file`) ab, sobald sie hinter dem
  Unterbefehl stehen (Optionen vor *und* nach dem Unterbefehl müssen funktionieren).
