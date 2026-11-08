---
name: cloud-browser-sessions
description: "Use when a headless agent needs a persistent-login browser."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [browser, cdp, browser-use, cloud-browser, login, cookies, headless, portal, 2fa]
    related_skills: [hermes-agent, sip-telephony, blocked-page-recovery]
    category: web
---

# Cloud Browser Sessions — Persistent Login and Raw CDP

Class of task: the agent runs headless (server, container, gateway) and needs a real browser that (a) keeps a portal login across turns, (b) exits from a country the site expects, or (c) is driven from a script rather than through its own browser tool. Includes handing the one-time login over to the human in a live view.

## When to Use

- The data lives behind a portal login (billing, telephony console, admin tooling) whose password/one-time code the agent must not type itself.
- The agent's own browser tool starts a throwaway profile per call — a `chrome-<uuid>` scratch dir wiped afterwards — so "remember this device" never survives and every visit costs a full login round trip.
- Site behaviour is geo-dependent (a `.de` console, geo-blocked pages): the session must run in that country, through a proxy there.
- Something is only reachable over raw CDP: cookie export/restore, request interception, attaching to an existing tab.

## Standing rules (user preferences, apply every time)

- **Never type a password, PIN or one-time code.** The human authenticates in the live view; the agent only observes and continues afterwards. Never ask for the code in chat either.
- **Never print session control URLs, cookies or tokens into the chat** beyond the live-view link the human needs to click.
- When a login has a "remember this device" checkbox, tell the user to tick it — but treat the persistent profile as *unconfirmed* until a later session actually shows the login still active.
- Do the whole portal walk in as few calls as possible: a lost session costs another e-mail/SMS round trip.

## Procedure

### 1. Create a session (Browser-Use cloud, verified)

```bash
KEY=$(grep -oP '^BROWSER_USE_API_KEY=\K.*' ~/.hermes/.env)
curl -s -X POST https://api.browser-use.com/api/v3/browsers \
  -H "X-Browser-Use-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"profileId":"<profile-uuid>","proxyCountryCode":"de","timeout":240}' \
  -o session.json
```

- `proxyCountryCode` is **lowercase ISO-2**; `timeout` is minutes and 240 is the ceiling.
- `profileId` (a stored browser profile) is what carries cookies across sessions; omit it for a disposable browser.
- The response holds `id`, `cdpUrl` (control) and `liveUrl` (human view). Keep it in a per-target file such as `~/.hermes/<target>/session.json` with `0600`.
- Status/cleanup: `GET https://api.browser-use.com/api/v3/browsers` lists sessions; stop one via `POST .../browsers/{id}/stop`.

### 2. Hand the live view to the human

Send the `liveUrl` with the exact expiry time converted to the user's timezone (session start + `timeout`), and say what to do there and what to report back. Then **wait** — do not poll or re-navigate while they work; navigating moves their page.

The live view **is** interactive in practice (verified: a user typed e-mail, password and an e-mail PIN into it and reached the portal) — so the human does the whole login there and the agent never needs a credential fill. If a live view ever turns out to be watch-only, fall back to the persistent profile (`profileId`) plus a credential-vault fill, or ask the user to log in on their own machine and export the cookie — do not ask for the password in chat.

### 3. Drive and read over CDP

`cdpUrl` is an **https** URL; websockets clients need **wss** — map `https://`→`wss://` (and `http://`→`ws://`). An instant connection failure with no error text usually means an unmapped scheme.

Use `scripts/cdp.py` in this skill (needs `pip install --user websockets`):

```
python3 cdp.py create [--profile UUID] [--proxy de] [--timeout 240]
python3 cdp.py ip            # public IP of the browser (proxy check)
python3 cdp.py nav <url>     # navigate, print url + title
python3 cdp.py text [n]      # visible page text (what a screen reader would get)
python3 cdp.py cookies       # every cookie: domain, name, expiry
```

It reads the session JSON from `--session` (default `./session.json`) and self-creates a page target when none is attached. The important CDP shape: `Target.getTargets` → `Target.attachToTarget {flatten:true}` for a `sessionId`, then every call carries that `sessionId`; `Runtime.evaluate {expression, returnByValue:true}` is the workhorse (`document.body.innerText`, `location.href`, `document.title`). `Network.enable` must precede `Network.getAllCookies`.

Do **not** wrap the CDP URL in the agent's own browser tool — that tool opens its own browser and ignores an existing session.

### 4. Persist beyond the session window

Two independent mechanisms — set up both, verify each:

- **Profile:** `profileId` at creation time (server-side cookies, survives the session).
- **Cookie export:** right after the human logs in, enable `Network`, then `Network.getAllCookies`, filter to the portal domain, and write them to a `0600` file next to `session.json`. This is the durable fallback: it works even if the profile did not attach, and it can be re-injected later (or replayed as a `Cookie:` header for plain fetches).

Re-read the portal when you return: if the tab is `about:blank` or a fresh new-tab page, the login did not survive — re-run step 1 and hand the live view over again rather than reporting data you could not read.

## Pitfalls

- **Verify the attachment, do not trust the request.** The create response may not echo `profileId`/`proxyCountryCode`. Fetch the browser's public IP *through the session* (`cdp.py ip`) and compare it with the expected country; a mismatch means the proxy did not apply.
- **A config switch is not a behaviour switch.** Changing the agent's own browser backend (`hermes config set browser.cloud_provider browser-use`) only affects newly started processes — restart the gateway (`systemctl --user restart hermes-gateway`) before believing it, and confirm by checking whether a new cloud session appears in the API list after one browser call.
- **A session has a hard expiry** (240 min on Browser-Use). Harvest something durable before the window closes; never plan multi-day work around one session. Tell the user the expiry in their local time.
- **The agent's own tool-started cloud sessions are typically per-session** (no profile), so a login done there is gone by the next call. That is the whole reason to keep a dedicated session plus a cookie store.
- **Cookies are credentials**: mode `0600`, path reported, never in the transcript; delete them when the arrangement ends. A portal's own "remember this device" cookie is the useful one (e.g. `trusted_device`) — read its expiry and tell the user that date, since it usually outlives the browser session by weeks.
- **Prove an empty list instead of reporting "probably nothing"**: when a portal page says "no entries", submit the page's own export form from inside the page (`new FormData(form)` → `fetch(action, {method:'POST', body:fd, credentials:'same-origin'})`) and read the response body. A CSV with nothing but the header row is hard evidence that the list is genuinely empty rather than filtered by an unnoticed default.
- A logged-in session is also the most trustworthy evidence about a provider's own configuration (routing tables, block/filter lists). Portal screenshots are unverifiable for a blind user — extract text and quote the exact list you read.

## Verification checklist

1. Session created; `id`, `cdpUrl`, `liveUrl` stored `0600`; no control URL dumped in chat.
2. Public IP fetched through the session matches the intended country.
3. Human confirmed the login; cookies or profile confirmed to carry it (re-open the portal and read a logged-in page).
4. Cookie file `0600`; expiry of the session and of the login both stated to the user.
