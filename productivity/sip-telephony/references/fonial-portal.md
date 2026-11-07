# Fonial Kundenkonto — portal walk for SIP credentials

Concrete paths and form behaviour observed in a Fonial Kundenkonto (FREE tier). Re-verify selectors before relying on them; the flows and the required-field traps are the durable part.

## Read existing credentials

1. `Telefonanlage → Ziele → IP-Endgeräte` (`/system/device/`) lists devices. Each row's action icons include "Benutzerdaten SIP-Konto" → `/system/device/<id>/sip`.
2. That page renders `Benutzername`, `Passwort`, `Server-URL`, `Proxy-URL` as plain `<input>` values — read them in-page. Two of the fields share the same `id` (`registrar`); take the first as server and the second as proxy.
3. The SIP page carries no dialable number. `SIP_NUMBER` comes from `Telefonanlage → Rufnummern` (the number assigned to the employee), written without spaces.
4. Write the file in the same call that reads the values (mode `0600`), and print only key names plus value lengths.

## Create a second IP-Endgerät for the agent

1. `Telefonanlage → Ziele` → "Neues Ziel anlegen" opens `/system/device/new`. The page shows only the target-type radios and no visible submit button; a JS `form.submit()` on that step does not advance the wizard. Go straight to `/system/device/ipdevice/new` instead — that is the URL the radio's own value points to.
2. Fill the creation form. `Modell` accepts a model id (`62` = Zoiper for a softphone; `other` = anderer Hersteller), `targetName` is the display name, MAC stays empty for a softphone.
3. **Two fields are required although they look optional:** Wartemusik (`..._moh`) and interne Nebenstelle (`..._internalext`). Missing either one makes the save return a validation-error page with "Bitte wählen Sie eine Wartemusik" / "Bitte geben Sie eine interne Nebenstelle ein". Set both, then submit again.
4. The outgoing number dropdown offers the account's numbers; reuse the employee's number is fine (a number can be shared across targets), the extension must be unique.
5. A successful save answers with a bare JSON redirect (`["\/system\/device\/"]`), not a rendered page. Verify by navigating to `/system/device/` and reading the row: name, model, extension, status (`Offline` is expected until something registers).
6. The new device's SIP credentials are on `/system/device/<new id>/sip`, same read-and-write-in-one-call pattern as above.

## Notes

- The FREE tier can hold devices without a dialable number; an empty `Rufnummern (0)` table next to a device list is normal and not an error.
- Device rows show `Offline` until a client registers — do not report that as a failure of the credentials.
- Optional reachability check without leaving a registration: `sipsak -vv -s sip:<user>@<server> -u <user> -a <pass> -H <proxy> -N`. A `200 OK` from FreeSWITCH proves server, DNS and auth path; a full REGISTER is a separate decision.
