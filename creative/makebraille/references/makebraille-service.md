# MakeBraille — Dienstdetails (Stand: Recherche 31.10.2026)

## Dienst

* Adresse: `https://makebraille.dzblesen.de/MakeBraille` (301-Weiterleitung von
  `dzblesen.de/makebraille` und `www.dzblesen.de/makebraille`).
* Betreiber: dzb lesen (Deutsche Zentralbücherei für Blinde, Leipzig).
* Zweck: automatische Umwandlung von MusicXML- und CapX-Dateien (CapX = mit capella gescannte
  Drucksätze) in Musikbraille.
* Zugang: Login mit Benutzername + Passwort, beide **maximal 30 Zeichen**; das Benutzernamenfeld
  akzeptiert laut HTML `pattern="[A-Za-z0-9_.-]*"`.
* Kontakt: `makebraille-support@dzblesen.de` (Konto, Probleme, Feedback).
* Förderung: DAISY Consortium, DAISY Music Braille Project (2020/2021).

## Nutzungsbedingungen (Sinngemäß, Quelle: Login-Seite, Stand 01.08.2024)

* Nur privat oder nicht-kommerziell.
* Konvertiert werden dürfen gemeinfreie Werke, rechtmäßig genutzte urheberrechtlich geschützte
  Werke und eigene Kompositionen/Sätze.
* dzb lesen überwacht die Nutzung, um den Dienst zu verbessern und Missbrauch zu verhindern.
* Die Verantwortung für eingereichte und konvertierte Dateien liegt beim Nutzer.
* Rückmeldungen sind ausdrücklich erwünscht (Mailadresse oben, Betreff `[Server] Feedback`).

## Beobachtetes Verhalten der Schnittstelle

* `GET /MakeBraille` → Login-Seite (Titel „MakeBraille — Login"), Formular `id="f"`,
  `method="post"`, `action="/MakeBraille"`, `enctype="multipart/form-data"` mit
  `input name="login"` (text) und `input name="passwd"` (password) sowie
  `button name="mode" value="server_login"`.
* `POST /MakeBraille` mit falschen Zugangsdaten und `mode=server_login` → HTTP **200** und wieder
  die Login-Seite (kein Redirect, keine Fehlermeldung im HTML). Die Erfolgsprüfung muss daher den
  Seiteninhalt auswerten (kein `name="passwd"` mehr, Titel ≠ Login).
* Andere `mode`-Werte ohne gültige Sitzung (`server_upload`, `upload`) liefern ebenfalls die
  Login-Seite — ohne Anmeldung ist nichts zu sehen, es gibt keinen Gastmodus.
* Kein CAPTCHA, kein CSRF-Token im Formular beobachtet; die Sitzung läuft über Cookies.

## Offene Punkte

* Das Formular **nach** dem Login (Upload, Optionen wie Braille-Zeichensatz/Format, Download-Weg)
  ist noch nicht dokumentiert — dafür ist ein gültiger Zugang nötig. Danach
  `scripts/run.sh dump` und die Felder hier ergänzen.
