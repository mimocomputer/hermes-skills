# BYO-SIP platform matrix

Capabilities as documented by each vendor (verify against the live docs before relying on a cell — this table is where to look, not a guarantee):

| Route | Auth to your provider | REGISTER | Inbound from your number | Cost shape |
|---|---|---|---|---|
| **Local Asterisk / FreeSWITCH** | whatever the provider offers, incl. REGISTER | yes (it registers) | provider forwards/rings that device, or a direct trunk INVITE | server only |
| **OpenAI Realtime / GPT-Live SIP** | `transport.trunk.auth.type: digest` + username/password, `provider_url` must be `sips:`/TLS, `caller_number` E.164 | no | point a provider-side forward at `sip:$PROJECT_ID@sip.api.openai.com;transport=tls` (+ webhook for `live.transport.incoming`) | $0.05/min voice layer + model tokens; SIP feature must be enabled on the project |
| **Vapi BYO SIP trunk** | `byo-sip-trunk` credential with `outboundAuthenticationPlan.authUsername/authPassword`; gateway by hostname (outbound) | no | inbound gateway needs a **numeric IPv4** address | platform per-minute + models |
| **LiveKit (Cloud or self-hosted)** | outbound trunk with `auth_username`/`auth_password`; inbound trunk with username/password, `allowed_numbers`, or `allowed_addresses` | no (explicitly unsupported) | provider must send the INVITE to the LiveKit SIP endpoint | Cloud free tier / self-host; SIP service deploys separately when self-hosting |
| **Twilio (Elastic SIP / BYOC)** | **not possible for origination** — "Twilio does not support authentication with the carrier via credentials for BYOC origination" | no | needs a Twilio number on the trunk | Twilio number + minutes |

Consequence of the "no REGISTER" column: if the provider only ever accepts traffic from a registered device, the local stack is the only option; if it accepts authenticated unregistered INVITEs (or can forward to a SIP URI), a hosted platform works.

## German cloud-PBX providers (Fonial as the worked example)

Measured from a server with a public IP (reproduce with `scripts/sip_probe.sh`):

- `sip.plusnet.de` answers an unauthenticated OPTIONS with `200 OK`, `User-Agent: FreeSWITCH`, and echoes `rport;alias` + `received=<public ip>` → reachable over UDP/5060, NAT handled provider-side, no NAT settings needed.
- Routing is SRV-based: `_sip._udp.sip.plusnet.de` lists twelve `voiceNN.sip.plusnet.de` targets on port 5060. Address the service host, not one node; a round-robin A record can pick a node that stays silent on unauth OPTIONS, so repeat a silent probe before concluding anything.
- The portal's `SIP_PROXY` value can be a name that does **not resolve in public DNS** (`proxy08.sip.plusnet.de` → NXDOMAIN) while `SIP_SERVER` works and SRV-routes. An unresolvable proxy is not a broken account — probe the server host.
- `sipsak` can print nothing on success without `-v`; re-run a silent probe with `-v` and grep the status line before drawing a conclusion.
- `REGISTER` with the SIP user returns `200 OK` (registered-device account); `-x 0` deregisters cleanly.
- Decisive test for this account: unregistered `INVITE` → `407 Proxy Authentication Required` → digest auth → `100 Trying` for a non-existent destination. The provider **accepts authenticated unregistered INVITEs**, so both the local stack and hosted BYO-SIP platforms are viable; the choice is cost/effort, not feasibility.
- Probe tooling: `scripts/sip_probe.sh` (sipsak OPTIONS/REGISTER); raw-socket unregistered-INVITE probe and raw-RTP announcement caller live with the agent (`~/.hermes/scripts/sip_invite_probe.py`, `sip_announce.py`) — no PBX and no sound card needed (audio: `ffmpeg -i in.mp3 -ar 8000 -ac 1 -f mulaw out.ulaw`, streamed in 160-byte packets, tail padded with 0xFF).

Portal/administration facts worth knowing before planning inbound:

- SIP credentials live in the customer portal under the phone system area (`Ziele` → IP device / `SIP-Benutzerdaten`); each employee/`Mitarbeiter` and each `IP-Endgerät` has its own username/password — ask for a separate one for the agent.
- Inbound routing is a `Ziel` plus a forwarding rule on the number; forwarding to an external **SIP URI** exists and is the way to point a number at a hosted platform. A third-party integration guide describes exactly that split (outbound = SIP user credentials authenticated against the provider's SIP host, inbound = forwarding to a SIP URI, the portal showing the SIP user permanently "Offline" because no REGISTER is ever sent) and states the voice-AI trunk capability needs the paid PLUS plan: https://docs.famulor.io/telephony/providers/fonial — vendor documentation of a third party, so verify in the portal.
- The provider's own service description states SIP accounts are provided "mit Registrierungsmechanismen", i.e. registration-based accounts: https://fonial.de/kontakt/leistungsbeschreibung-trunking
- Portal login is password + e-mail PIN; the PIN goes to whatever mailbox the account uses, so route that mailbox to Hermes when the account is the agent's.

### Fonial customer portal: the concrete paths

`kundenkonto.fonial.de` — login `/login`, e-mail-PIN step `/2fa`, dashboard `/`.

- `Telefonanlage` `/system/`; `Rufnummern` `/system/number/`, `Ansagen` `/system/prompt/`, `Ziele` `/system/device/`
- `Verwaltung` `/settings/` carries only password and tickets — there is no user administration, so an employee's SIP data is simply an `IP-Endgerät` under `Ziele`
- The SIP values sit on the `IP-Endgerät` detail page (tabs `IP-Endgeräte` / `Weiterleitungen` / `Mailboxen`). No device in the list = no SIP credentials in that account, whatever the dashboard tile says: a fresh `fonial FREE` account showed "1 Rufnummern aktiv" on the dashboard while `/system/number/` read `Rufnummern (0)` / "Keine Einträge vorhanden" and `Ziele` read "Es wurden noch keine IP-Endgeräte für Sie angelegt."

Mailbox hygiene for the e-mail PIN (AgentMail API, key `AGENTMAIL_API_KEY`): `GET /v0/inboxes/<inbox>/messages?limit=50` (paginate on `next_page_token`), keep those whose subject is the PIN subject, `DELETE /v0/inboxes/<inbox>/messages/<url-quoted RFC Message-ID>`, then re-list to confirm the count dropped. Julian wants the PIN mails gone after each portal login.
