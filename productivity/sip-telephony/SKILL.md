---
name: sip-telephony
description: "Use when an existing SIP number should make agent calls."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [telephony, sip, voip, asterisk, freeswitch, twilio, vapi, livekit, openai-realtime, calls, tts, stt]
    related_skills: [hermes-agent, makebraille]
    category: productivity
---

# SIP Telephony — Using an Existing Number or Trunk

Class of task: the user already owns a phone number reachable over SIP (a cloud PBX user, an IP phone account, a SIP trunk) and wants the agent to speak on calls, answer calls, or both — without buying a second number.

## When to Use

- The user offers SIP credentials (user, password, server, proxy) or a trunk and asks whether the agent can call with it.
- "Can we use my existing number instead of buying a Twilio number?"
- A hosted voice-AI platform has to be wired to a number the user already owns.
- Not for SMS: number-centric messaging needs Twilio or a similar sender, not a SIP account.

## What Hermes already ships

- Optional skill `official/productivity/telephony` — number-centric: buying a Twilio number, SMS/MMS, Twilio `<Say>`/`<Play>` calls, Bland/Vapi AI calls. It does **not** handle SIP credentials.
- Voice mode (STT/TTS providers, `/voice`) — the building blocks (make audio, record audio, transcribe) but not a phone transport.
- No SIP client, no SIP registration, and no provider-credential support in core.

So the work is: establish the SIP facts by measurement, then either run a local SIP stack or hand the trunk to a hosted platform.

## Procedure

### 1. Establish the shape before touching anything

Ask (or read from the provider portal):

- **Cloud PBX number or trunk?** A PBX number is routed by the provider's own dial plan (`Ziele`, `Rufnummern`, forwardings); a trunk is addressed directly from a PBX the user owns. The inbound story differs completely.
- **A separate SIP user for the agent?** Require one. Most providers allow only one REGISTER per SIP user, so sharing the user's softphone credentials makes the two registrations evict each other. Creating a second SIP user / `IP-Endgerät` also avoids disturbing their phone.
- **Inbound routing options:** can the provider forward a call to an arbitrary SIP URI (`Weiterleitung auf SIP-URI`), or point at a static IP? If neither, inbound to a hosted platform is impossible and the local-stack route is the only one.
- **Terms:** some providers gate trunk/voice-AI features behind a paid tier. Check the portal, do not assume.

### 2. Get the credentials in without the chat

Never collect a password in chat. Preferred: user writes a `0600` env file the probe and later the SIP stack source (`$HERMES_HOME/sip.env` with `SIP_SERVER`, `SIP_PROXY`, `SIP_USER`, `SIP_PASSWORD`, `SIP_NUMBER`). The browser credential vault is a **browser-fill store** — it cannot feed a daemon. For the full ladder (env file vs `secrets.command` + `terminal.env_passthrough` vs in-process vault resolution) and for extracting a SIP password that is only shown in a provider portal, read the `hermes-agent` skill, section "Secrets that a service (not a browser page) must read".

When the values only exist in the provider portal, the order is: confirm the credential exists, then extract, then write the file.

- **Confirm first.** Open the provider's device / SIP-user list and check that the named `IP-Endgerät` / `Mitarbeiter` / SIP user is actually there. An account can be legitimate and still have zero devices; then there is nothing to extract and the answer is the empty inventory, never a `sip.env` with invented or blank values.
- **Extract without the chat.** Enter the identifier, fill the password with `browser_vault_fill`, submit, and let `browser_vault_enter_code` supply the one-time / e-mail PIN. Never read a verification code out of the mailbox yourself and never type one — write the retrieved values straight into the `0600` file from the same call that reads them, so no secret passes through stdout or the transcript.
- **Clean up after the login.** When the PIN is delivered by e-mail, delete those mails from the mailbox once the session is up (filter on the PIN subject, then re-list to confirm). AgentMail's REST base is `https://api.agentmail.to/v0/...`; `/v1/` returns a 404 route-not-found for every path, so a 404 there means the wrong version prefix, not a bad key.
- **One credentials file per SIP user.** Keep the user's/employee's device in `sip.env` and the agent's own device in a separate file (`sip-agent.env`); never overwrite the first when the second is created. Report both paths, their modes, and which device each belongs to.

Portal-sourced credentials (Fonial example): the Kundenkonto lists `Telefonanlage → Ziele → IP-Endgeräte`; each row's first action icon links to `/system/device/<id>/sip` ("Benutzerdaten SIP-Konto"), which renders Benutzername, Passwort, Server-URL and Proxy-URL as plain input values — read them in-page and write the env file directly, never through stdout. The number shown there is the extension; the dialable `SIP_NUMBER` comes from `Telefonanlage → Rufnummern` (assigned `Mitarbeiter`). A Fonial Kundenkonto session expires quickly between agent turns and re-login needs an email PIN, so do portal work in as few calls as possible. The mechanism behind the constant re-logins: the agent browser starts a throwaway profile per call (`~/.hermes/cache/scratch/agent-browser-chrome-<uuid>`, wiped afterwards), so the "Dieses Gerät als vertrauenswürdig speichern" cookie dies with the profile — the checkbox does work, it just does not survive the session. Plan one continuous portal walk per call sequence instead of relying on a persistent login.

When the account already holds the user's device and you need a second one for the agent: create it in the portal rather than reusing their credentials. Fonial creation walk, form quirks and the credentials-file split are in `references/fonial-portal.md`.

### 3. Probe before designing anything

Run `scripts/sip_probe.sh` (needs `sipsak`, `apt-get install -y sipsak`). It does, in order: unauth OPTIONS → auth OPTIONS → optional REGISTER. Read the results like this:

- `200 OK` / `401` / `407` on unauth OPTIONS = the endpoint is reachable and speaks SIP. The `User-Agent` in the reply tells you what the provider runs (a FreeSWITCH `200 OK` means a softswitch answers, which usually tolerates several registration/NAT shapes).
- **Timeout on the user's main SIP server but a response on the proxy host** is common: the registrar may only answer on TLS/5061 or on the proxy host. Probe the exact `SIP_PROXY` value, not just the obvious hostname.
- `rport;alias` + `received=<public ip>` in the response = the provider detects the public IP itself; NAT settings can stay off and no router port-forwarding is needed for outbound/registration.
- Auth OPTIONS failing while the endpoint answers means wrong user/password/realm, not a network problem.
- `-x 60` (REGISTER, expires 60) succeeding = classic registered-device account; `-U` afterwards unregisters so a test never leaves a stale registration behind.

### 4. Run the decisive test: authenticated INVITE with no REGISTER

Every hosted platform below **never sends a SIP REGISTER** — it dials the provider with digest credentials. Whether that works is a property of the provider and can only be measured: place an authenticated INVITE from a fresh client that never registered. If the provider rejects it, hosted platforms are out and the local stack (a real REGISTER) is the only path. Do not promise a hosted route before this measurement.

### 5. Choose the route

See `references/providers-and-platforms.md` for the capability matrix with sources. Short version:

- **Local Asterisk or FreeSWITCH** (register as a device/`IP-Endgerät`): always works when the provider supports registration, no per-minute platform fee, full audio control. Bridge the agent with `ARI` + ExternalMedia, the AudioSocket channel, or the WebSocket media channel; a minimal first milestone is register → answer/place → play a TTS file → record → transcribe. Open-source scaffolding exists in the AgentVoiceResponse project (Asterisk + AudioSocket + ASR/LLM/TTS docker-compose).
- **Hosted BYO-SIP** (Vapi, LiveKit, OpenAI Realtime/GPT-Live SIP): faster to a conversational agent, billed per minute, and dependent on step 4. Each has its own inbound twist (trunk vs SIP-URI forward vs numeric-IP gateway).
- **Minimal POC without a PBX:** `pjsua`/`baresip` registers and can play a generated file or record a call — good enough to prove registration, credentials and caller ID before building.

### 6. Wire it to Hermes

Generate prompts/answers with `text_to_speech`, transcribe recordings with the configured STT provider, expose the call as a small CLI or skill script (`call <number> <text>`), and confirm with the user before dialing. Emergency numbers never.

### 7. Local stack on the agent host (measured, Asterisk 22 / Debian-Ubuntu ARM)

`apt-get install -y asterisk` gives a working PJSIP stack; no sound card needed for `Playback`. Two traps cost most of the time:

- **pjlib's bundled resolver fails on zones with 12 A-records and no AAAA**: `pjsip_resolver.c: Resolution completed - 0 viable targets` → registration ends as `503 No answer record in the DNS response (PJLIB_UTIL_EDNSNOANSWERREC)`. `dig` resolves the same name fine; only Asterisk's resolver is broken. Fix: pin one SRV/A target by IP in the config generator (`dig +short SRV _sip._udp.<host>` → first target → its first A record) and use that IP in `server_uri` and the aor `contact`, keeping the hostname in `client_uri`/`from_domain`. Regenerate with a script that reads `sip.env` so the password never passes through stdout.
- **Behind NAT** (Oracle: private `10.x` + 1:1 public IP) set `external_media_address` / `external_signaling_address` to the public IP and list `local_net` for the private ranges, plus `direct_media=no`, `rtp_symmetric=yes`, `force_rport=yes`, `rewrite_contact=yes`.
- Enable a text SIP trace only when needed: uncomment `full.log => ...debug,verbose...` in `/etc/asterisk/logger.conf`, `logger reload`, `pjsip set logger on`, then grep `/var/log/asterisk/full.log`. `pjsip show registrations` gives the one-line status (`Registered (exp. 1545s)` / `Rejected`).
- Test calls headless with `asterisk -rx "channel originate PJSIP/<dest>@<endpoint> extension s@<context>"`; the dialplan plays the announcement. Read the outcome from the log line `Response is <code>` instead of parsing the CLI output.
- A mature stack also tells the *provider's* verdict apart from your own signalling: `407` before/after `403` means auth is fine and the **account policy** refuses (`403 Forbidden`, `Content-Length: 0`, no reason phrase). Expect 403 when the SIP user has no outbound right and stop probing dial formats — see the next pitfall.

## Pitfalls

- **A `403 Forbidden` on every outbound INVITE is an account-permission finding, not a codec/CLI/format problem.** Measure a small matrix (from_user with/without `+`, national vs E.164, landline vs mobile vs bogus destination) before concluding: if *all* of them answer 403 within milliseconds, the provider's softswitch is refusing the SIP user wholesale. On a hosted cloud-PBX product the SIP user is a *phone line* of that PBX, and Fonial separates inbound-number rights from **outbound-number rights**: `Mitarbeiter verwalten` → the employee profile has its own tab for `Ausgehende Rufnummer` ("erlaubt dem Mitarbeiter, die Rufnummer ausgehend in seinem IP-Endgerät zu setzen"). Only the account owner can grant that. On a *Trunking* account the equivalent step is `Rufnummern` → select number → `SIP-Benutzer zuordnen`. Ask for the missing grant, do not keep re-dialling.
- Hosted voice-AI platforms never REGISTER — check step 4 before recommending one.
- Twilio cannot import a foreign number: BYOC origination explicitly rejects carrier credential auth (the carrier must trust Twilio's IPs), so "bring my SIP number to Twilio" is a dead end. A number verified as **Verified Caller ID** only gives *outbound voice* with that number as caller ID (voice-only, per account, best effort in some countries); SMS senders always require a Twilio number.
- Vapi's inbound gateways accept a numeric IPv4 address only; a DNS name works outbound but not inbound.
- LiveKit never registers either, and inbound username/password auth depends on the provider supporting it (Twilio Elastic SIP does not).
- One registration per SIP user — never share the user's softphone credentials with your stack.
- An empty device list is a finding, not a failure: report "no IP-Endgerät / SIP user exists in this account yet" and stop, rather than producing a placeholder credential file.
- Re-check the portal session instead of trusting an earlier success: if the tab is `about:blank` or a fresh `chrome://newtab` at the start of a turn, the cookies are gone and the read will silently return the login page. Batch the whole portal walk (fill → vault password → submit → vault code → submit → read target page) into consecutive calls, because a session loss costs a full e-mail-PIN round trip.
- Provider dashboards can contradict their own list pages (a tile counting "1 Rufnummern aktiv" above an empty `Rufnummern (0)` table). Trust the list/detail pages you would extract from, and say which one you read.
- Don't report a hosted path as "the recommended approach" until the INVITE test has actually succeeded; label measured facts and vendor documentation separately.
- This user expects provenance: state which claim was measured here, which came from vendor docs (link it), and disclose search/fetch fallbacks when the configured backend fails mid-research.

## Verification checklist

1. Probe script ran; endpoint, protocol and auth result recorded.
2. REGISTER test left no stale registration (`-U`).
3. Authenticated INVITE without REGISTER answered → route decision justified.
4. Credentials live in a `0600` file, never in chat or argv — and the target device/SIP user was confirmed to exist in the portal, or the empty inventory was reported.
5. Any e-mail PIN mails generated by the portal login are cleaned up afterwards.
6. No rule about the user's own softphone/SIP user is broken (separate user used).
7. Each SIP user has its own `0600` env file; a newly created portal device is confirmed in the device list (name, extension, status) and its SIP page re-read, not assumed from the save response.
