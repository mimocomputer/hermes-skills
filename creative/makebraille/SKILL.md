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
scripts/run.sh config                      # aktives Profil, Empfängeradresse, Einstellungen
scripts/run.sh config --save --name NEU --email ADRESSE   # Profil klonen/ändern
```

`config` liest die Konfigurationsseite. Mit `--save` wird sie mit den **vorhandenen** Werten
abgeschickt und dabei nur Profilname (`--name`) und/oder Empfängeradresse (`--email`) ersetzt —
so entsteht aus einem bestehenden Profil ein Klon mit denselben Einstellungen. Achtung: die
Seite gehört zum echten Konto, unabgeschickt (`--name`/`--email` ohne `--save`) liest sie nur.

## Ergebnis: kommt per E-Mail

MakeBraille hat **keinen Download in der Weboberfläche**: die fertige Datei wird automatisch an
die Adresse geschickt, die im aktiven Profil steht (Absender `no-reply@dzblesen.de`, laut Hilfe
innerhalb von 30 Minuten, bei Ausbleiben Spam-Ordner prüfen). Für einen unbeaufsichtigten
Ablauf muss die Zieladresse also eine sein, die der Agent lesen kann (AgentMail-Postfach) — dann
ist der Kreislauf Upload → Mail → Datei einlesen geschlossen. Ein Profil auf eine
AgentMail-Adresse umzustellen ändert nur dieses Profil, nicht die eigenen.

## Profile und Antwortformen (Stand 31.10.2026)

* **Klon steht bereit:** Profil `Hermes-AgentMail` im Konto (Kopie von `Chor`, Empfänger
  `mimo@agentmail.to`). Für eigene Läufe `--profile Hermes-AgentMail` setzen; `Chor` bleibt
  Julians Profil mit seiner Adresse.
* **Die Empfängeradresse ist profilweit.** Nachweis: Adresse im Klon geändert, `Chor` blieb
  unverändert. Beim **Anlegen** eines Klons mit `config --save --name NEU --email ADDR` wurde die
  neue Adresse nicht übernommen — erst ein zweiter Speichervorgang unter dem neuen Namen setzte
  sie. Also: anlegen, zurücklesen, Adresse ggf. nachziehen.
* **Profilwechsel ist ein eigener Schritt** (`mode=switch_uprofile`) und muss vor dem Upload
  passieren; danach prüfen (das aktiv gewählte `<option ... selected>`); ein
  `uprofile_selector` im Upload-POST allein wechselt das Profil nicht.
* **Drei Antwortformen auf einen Upload:** (a) Danke-Seite „Your converted music Braille file
  will be sent to: <adresse>." — akzeptiert, nennt die Zieladresse (beste Bestätigung),
  (b) Startseite mit „Your file is still being converted, please wait." — angenommen,
  (c) leere Antwort (HTTP 200, 0 Byte) — keine Bestätigung, Upload wiederholen. Welche Form
  kommt, hängt offenbar vom Serverzustand ab, **nicht** vom Profil: `Chor` und
  `Chor_Direktausgabe` haben feldweise identische Einstellungen (44/46 gleich, nur der Name
  differiert) und lieferten dennoch beide Formen.
* **Der Upload-POST trägt die kompletten Profileinstellungen** (u. a. `email`, `paper_width`,
  `text_format`, `filter_*`) — nach dem Profilwechsel also immer das Formular der frischen Seite
  verwenden, nie ein vorher eingesammeltes.

Ohne Vault (andere Umgebung): `--user <name> --password-file <datei>`. Passwörter **nie** als
Kommandozeilenargument übergeben — sie stehen sonst in der Prozessliste.

## Stand und Grenzen

* **Geprüft:** Vault-Anlage über beide Wege, Vault-Auflösung, HTTP-Sitzung (Cookies), Login-POST
  auf `/MakeBraille` mit `login`/`passwd`/`mode=server_login` und die Fehlererkennung — eine
  falsche Kennung liefert wieder die Login-Seite, der Client meldet „Login abgelehnt".
* **Upload (am Nutzer bestätigt, 31.10.2026):** der POST geht mit den aus der Startseite gelesenen
  Formularfeldern und dem Dateifeld `file` (nimmt `.capx`, `.musicxml`, `.mxl`, `.mxml`, `.xml`,
  `.zip`; Profil/Schalter vorher per `switch_uprofile`) an `/MakeBraille`; zwei Testkonvertierungen
  kamen als Mail an. Der Dienst antwortet auch bei Annahme nur mit der Startseite — daraus lässt
  sich **keine** Bestätigung ableiten. Beleg ist allein die Ergebnis-Mail; eine Konvertierung gilt
  erst als erledigt, wenn die Datei da ist.
* **Profil/Einstellungen** (Stand 30.10.2026, Konto julian.dreykorn): Profile `Chor`,
  `Chor_Direktausgabe`, `Nach_Systemen_Fingersätze`, `Orgel`, `Orgel_Englisch`, `Profil1_20220206`;
  Felder `makebraille_out_format` (z. B. `braille`), `country`, `user_profile`, `text_format`,
  `division`, `merge_parts`. Formular-`mode`-Werte: `server_login`, `create`,
  `switch_uprofile`, `delete_uprofile`, `configuration`, `part_excerpt_edit`.
* **Kein Login = keine Auskunft:** Der Dienst beantwortet jeden Aufruf ohne gültige Sitzung mit
  HTTP 200 und der Login-Seite — deshalb prüft der Client den Inhalt, nicht den Statuscode.

## Stolpersteine

* Origin-Bindung ist exakt: ein für `dzblesen.de` gespeicherter Login gilt nicht für
  `makebraille.dzblesen.de` und umgekehrt.
* `https://dzblesen.de/makebraille` und `https://www.dzblesen.de/makebraille` leiten per 301 auf
  `https://makebraille.dzblesen.de/MakeBraille` weiter — immer die Endadresse als Origin nehmen.
* Der Vault-Eintrag gehört ins Standardprofil; in Cron-/Webhook-Sitzungen funktioniert er
  weiterhin (lokale Vault-Einträge brauchen keinen Prompt), in fremden Profilen nicht.
* Wahlfelder (`radio`/`checkbox`) müssen **nur angehakt** mitgeschickt werden, sonst setzt ein
  `--save` auf der Konfigurationsseite ungewollt die zuletzt gelesenen Werte. `FormParser` merkt
  sich `checked`/`disabled`, `_form_fields` verwirft nicht angehakte Wahlfelder.
* Neue Unterbefehle im Client brauchen `parents=[common]`, sonst lehnt argparse die globalen
  Optionen (`--out`, `--handle`, `--user`, `--password-file`) ab, sobald sie hinter dem
  Unterbefehl stehen (Optionen vor *und* nach dem Unterbefehl müssen funktionieren).
