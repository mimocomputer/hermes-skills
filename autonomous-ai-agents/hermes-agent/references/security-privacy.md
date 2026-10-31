# Security & Privacy Toggles

Common "why is Hermes doing X to my output / tool calls / commands?" toggles — and the exact commands to change them. Most of these need a fresh session (`/reset` in chat, or start a new `hermes` invocation) because they're read once at startup.

### Secret redaction in tool output

Secret redaction is **on by default** — tool output (terminal stdout, `read_file`, web content, subagent summaries, etc.) is scanned for strings that look like API keys, tokens, and secrets before it enters the conversation context and logs. Leave it enabled for normal use:

```bash
hermes config set security.redact_secrets true       # keep enabled globally
```

**Restart required.** `security.redact_secrets` is snapshotted at import time — toggling it mid-session (e.g. via `export HERMES_REDACT_SECRETS=false` from a tool call) will NOT take effect for the running process. Tell the user to change it in config from a terminal, then start a new session. This is deliberate — it prevents an LLM from flipping the toggle on itself mid-task.

Disable only when you deliberately need raw credential-like strings for debugging or redactor development:
```bash
hermes config set security.redact_secrets false
```

### PII redaction in gateway messages

Separate from secret redaction. When enabled, the gateway hashes user IDs and strips phone numbers from the session context before it reaches the model:

```bash
hermes config set privacy.redact_pii true    # enable
hermes config set privacy.redact_pii false   # disable (default)
```

### Command approval prompts

By default (`approvals.mode: smart`), Hermes asks an auxiliary LLM to assess shell commands flagged as destructive (`rm -rf`, `git reset --hard`, etc.). The modes are:

- `smart` — auto-approve a low-risk command once, deny high-risk commands, and prompt when uncertain (default)
- `manual` — always prompt
- `off` — skip all approval prompts (equivalent to `--yolo`)

```bash
hermes config set approvals.mode smart       # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

Per-invocation bypass without changing config:
- `hermes --yolo …`
- `export HERMES_YOLO_MODE=1`

Note: YOLO / `approvals.mode: off` does NOT turn off secret redaction. They are independent.

### "Reset permissions" / "make Hermes ask again"

The user usually means: wipe the accumulated "Always allow" state — NOT yolo
mode, and NOT a per-edit diff prompt (which doesn't exist; file writes never
go through the approval prompt, only shell commands do). Two stores hold it:

1. Shell-command allowlist: `hermes config set command_allowlist '[]'`
2. Shell-hook consent (only if present): `rm -f ~/.hermes/shell-hooks-allowlist.json`

Then sanity-check `hermes config get approvals.mode` (should not be `off`)
and confirm `--yolo` isn't baked into their launch alias or systemd unit.

### Shell hooks allowlist

Some shell-hook integrations require explicit allowlisting before they fire. Managed via `~/.hermes/shell-hooks-allowlist.json` — prompted interactively the first time a hook wants to run.

### Getting a password into the vault from a chat-only session

Masked vault prompts (`browser_vault_save_login`, `browser_vault_enter_code`, `browser_vault_unlock`) exist only on interactive surfaces: the CLI/TUI (`cli.py`, `hermes_cli/cli_*_mixin.py`, `tui_gateway/agent_callbacks.py`) and the desktop app install the prompt callbacks. A gateway/chat session (Matrix, Telegram, …) installs none, so `can_prompt_here()` is false and those tools answer `prompt_unavailable`. Whatever the user types in chat is an ordinary message and lands in model context, the session DB and the platform server; redaction can mask a value it already knows, not un-see one. Never invite a password in chat — say so and offer a route below instead.

Routes that keep the value out of the conversation (verified):

- One masked prompt on the user's own terminal — the piped lines answer the *visible* questions, the two `getpass` prompts (password, optional TOTP seed) read from `/dev/tty`:
  ```bash
  printf 'login\n<label>\n<scheme://host>\n<email|phone|username>\n<identifier>\n' | hermes vault add
  ```
  With no TTY at all (agent-run, headless) `getpass` falls back to stdin with a warning, which is how an agent can import a credential file whose value it must never print.
- Desktop app → Settings → Passwords & Logins → Add.
- `hermes vault list` shows handles + metadata (label, origin, identifier) and is safe to call from a chat session; local items need no unlock prompt to be listed or filled.

A login item is bound to scheme + host only (`normalize_origin` drops the path), e.g. `https://makebraille.dzblesen.de`; fills are refused on every other origin.

Pitfall: `browser_vault_fill` evaluates the page through Hermes' own supervisor (`tools/browser_supervisor`), which attaches to local and CDP-override browser sessions. On a host configured for a cloud backend (`browser.cloud_provider: browser-use`) the fill failed with "Could not determine the current page origin" even though `browser-use --doctor` showed the page attached and `browser_exec` could read it. Switching to `browser.cloud_provider: local` needs a Chromium the harness can attach to (`browser-use --doctor` reports `chrome-not-running` otherwise), and an already-running session keeps the old backend until it is recycled.

### Disabling the web/browser/image-gen tools

To keep the model away from network or media tools entirely, open `hermes tools` and toggle per-platform. Takes effect on next session (`/reset`). See `references/configuration.md` for the toolset list.

