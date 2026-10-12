# Troubleshooting

### Voice not working
1. Check `stt.enabled: true` in config.yaml
2. Verify provider: `python -c "import pm; pm.sync_venv(['stt-whisper'], explicit=True)"` or set API key
3. In gateway: `/restart`. In CLI: exit and relaunch.

### Tool not available
1. `hermes tools` — check if toolset is enabled for your platform
2. Some tools need env vars (check `.env`)
3. `/reset` after enabling tools

### Model/provider issues
1. `hermes doctor` — check config and dependencies
2. `hermes auth` — re-authenticate OAuth providers (or `hermes auth add <provider>`)
3. Check `.env` has the right API key
4. **Copilot 403**: `gh auth login` tokens do NOT work for Copilot API. You must use the Copilot-specific OAuth device code flow via `hermes model` → GitHub Copilot.

### Browser Use cloud: "no registered browser plugin has that name" / harness looks for local Chrome

Two independent config traps (not credential problems):

1. **The bundled `browser/browser_use` plugin must be ENABLED.** It ships in
   `plugins.disabled` on some installs; while disabled its `register()` never runs,
   so the `browser-use` cloud provider is never registered and ANY provider
   resolution raises `ValueError: browser is configured to use 'browser-use' ...
   no registered browser plugin has that name` (this even crashes `hermes doctor`,
   in the Chromium check). Fix: `hermes plugins enable browser/browser_use`.
   Takes effect on the NEXT session — a running CLI/gateway process keeps the
   cached negative resolution until restarted.

2. **`browser.backend` must be UNSET for cloud autospawn.** An explicit
   `browser.backend: browser-use` (what the `hermes tools` "Browser Use" CLI row
   writes) makes `is_legacy_browser_use_cloud_config()` return False, so Hermes
   never sets `BU_AUTOSPAWN` and browser_exec falls back to a local Chrome
   ("chrome-not-running"). Browser Use CLI mode is the DEFAULT when
   `browser.backend` is unset, so removing it loses nothing.

Working direct (BYOK, no Nous) Browser Use cloud setup:
```bash
hermes plugins enable browser/browser_use
hermes config unset browser.backend      # default = Browser Use CLI mode
hermes config set browser.cloud_provider browser-use
# .env:  BROWSER_USE_API_KEY=<your browser-use key>
```
`browser-use auth login` (stored at `~/.config/browser-harness/auth.json`)
configures the harness's OWN login, but Hermes's cloud-autospawn gate ONLY
checks the `BROWSER_USE_API_KEY` env/.env var — copy the key from auth.json into
`.env` (or use a key from browser-use.com). `BROWSER_USE_API_KEY` is in the
browser subprocess passthrough list, so `.env` reaches the harness. Verify:
a `browser_exec` run whose daemon log (`~/.config/browser-harness/tmp/bu-*.log`)
says `connecting to wss://...cdp.browser-use.com` = real cloud browser.

### Changes not taking effect
- **Tools/skills:** `/reset` starts a new session with updated toolset
- **Config changes:** In gateway: `/restart`. In CLI: exit and relaunch.
- **Code changes:** Restart the CLI or gateway process

### web_extract shows a stale page (result caching)
`web_search`/`web_extract` cache results for 20 minutes (PR #94618) — a
repeat fetch of the same URL within the TTL is served from cache, which
can look like "my website changes aren't showing up."

Automatic carveouts (always fetched live, never cached):
- localhost / 127.0.0.1 / `*.local` / `*.localhost` / single-label LAN
  hostnames / private + link-local IP ranges (dev servers, hot-reload
  builds, chat-GUI artifact previews)
- URLs matched by `security.website_blocklist`
- failed responses and keyless-rescue-served responses

Developing a site tested over the PUBLIC internet (Vercel/Netlify
preview, ngrok/cloudflared tunnel, staging domain)? Public DNS isn't
auto-carved-out — list the host in config.yaml:

```yaml
web:
  cache_exempt_hosts:      # always fetched live; effective immediately
    - mysite.vercel.app
    - "*.ngrok-free.app"
    - mysite.dev           # suffix match: also covers preview.mysite.dev
```

Blunt instruments: `web.cache_ttl_minutes: 1` (min) or
`web.cache_enabled: false` disables both caches entirely.

### Skills not showing
1. `hermes skills list` — verify installed
2. `hermes skills config` — check platform enablement
3. Load explicitly: `hermes -s name` (or the skill's own `/<name>` slash command)

### Gateway issues
Check logs first:
```bash
grep -i "failed to send\|error" ~/.hermes/logs/gateway.log | tail -20
```

Common gateway problems:
- **Gateway dies on SSH logout**: Enable linger: `sudo loginctl enable-linger $USER`
- **Gateway dies on WSL2 close**: WSL2 requires `systemd=true` in `/etc/wsl.conf` for systemd services to work. Without it, gateway falls back to `nohup` (dies when session closes).
- **Gateway crash loop**: Reset the failed state: `systemctl --user reset-failed hermes-gateway`

### Gateway runs but reports `No adapter available for matrix`

Check `hermes plugins show matrix-platform` before reinstalling dependencies.
Matrix is a bundled platform plugin; a disabled plugin leaves systemd active
but the gateway only executes cron jobs. If Matrix is configured and the
plugin is disabled, run `hermes plugins enable matrix-platform`, restart the
actual supervising service, then verify fresh gateway logs contain both
`matrix connected` and initial-sync completion. E2EE cross-signing warnings
are a separate issue; do not rotate keys or discard the crypto store just
to silence them. `hermes plugins doctor` may require the bundled plugin's
absolute directory rather than its display name. To obtain the composed
runtime command, use `hermes --print-runtime-command --module MODULE`;
`--run-module` is a launcher execution flag, not a print-runtime flag.

### Matrix deps fail to build: `python-olm` / libolm vs CMake >= 4

Symptom: `hermes pm install` (or the gateway's auto-install) fails with
`python-olm ... subprocess.CalledProcessError: Command '['cmake', '.', '-Bbuild',
'-DBUILD_SHARED_LIBS=NO']' returned non-zero exit status 1`, so the gateway logs
`requirements not met (pip install 'mautrix[encryption]')` and
`No adapter available for matrix`.

Cause: `mautrix[encryption]` depends on `python-olm`, whose sdist vendors libolm
with a `cmake_minimum_required` below 3.5 — rejected by CMake >= 4 (Debian
forky/sid ships 4.x). It is only built from source when PyPI has no wheel for
the running Python (python-olm ships wheels up to cp312; Hermes' bundled Python
is newer).

Fix:
```bash
export CMAKE_POLICY_VERSION_MINIMUM=3.5   # persist in ~/.bashrc
hermes pm install --extra matrix
systemctl --user restart hermes-gateway
```
A second, separate trap: setuptools uses the interpreter's sysconfig `CXX`, and
Hermes' bundled Python records `clang++`. On a host with only gcc/g++ the build
dies with `No such file or directory: 'clang++'` — install clang (or export
`CXX=g++`).

Verify success in `~/.hermes/logs/gateway.log`: `Matrix: E2EE enabled`, `initial
sync complete`, `✓ matrix connected`. The built wheel is cached by uv, so later
syncs reuse it; a cleared cache or fresh venv needs the env var again.

### Platform-specific issues
- **Discord bot silent**: Must enable **Message Content Intent** in Bot → Privileged Gateway Intents.
- **Slack bot only works in DMs**: Must subscribe to `message.channels` event. Without it, the bot ignores public channels.
- **Windows-specific issues** (`Alt+Enter` newline, WinError 10106, UTF-8 BOM config, line endings): see `references/windows-quirks.md`.

### Auxiliary models not working
If `auxiliary` tasks (vision, compression, session_search) fail silently, the `auto` provider can't find a backend. Either set `OPENROUTER_API_KEY` or `GOOGLE_API_KEY`, or explicitly configure each auxiliary task's provider:
```bash
hermes config set auxiliary.vision.provider <your_provider>
hermes config set auxiliary.vision.model <model_name>
```

### "Reset permissions" / auto-approving everything
See `references/security-privacy.md` — wipe the "Always allow" stores, don't touch yolo mode.

