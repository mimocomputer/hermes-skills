---
name: hermes-state-backup
description: Auto-backup skills/memory/config to git via inotify+systemd.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [git, backup, systemd, inotify, skills, memory, config, self-improvement]
    category: autonomous-ai-agents
    related_skills: [hermes-agent]
---

# Hermes State Backup

## When to Use

The user wants their Hermes state — skills (especially agent/curator-created
ones), memories, and config — durably version-controlled instead of living
only on one disk. This matters most right after the curator or an agent
creates/patches a skill autonomously: that content did not come from the
user typing it, so losing it is a real information loss, not just an
inconvenience. Also applies to: "back this up", "put this in git", "what if
the server dies", or any request to make self-improvement durable.

## Core Design: Two Repos, Never One

Split into a **public-safe** repo and a **strictly-private** repo — don't
lump them into one, because their sharing/visibility future differs and
their content-sensitivity differs:

1. **Skills repo** at `~/.hermes/skills/` (or `$HERMES_HOME/skills/`) — the
   live directory itself becomes the git repo (skills are already just
   text files, no secrets). Could plausibly go public/shared later.
2. **Private config/memory repo** — a **separate directory** (e.g.
   `~/.hermes/private-config-backup/`) that holds *copies* of:
   - `memories/MEMORY.md`, `memories/USER.md`
   - `config.yaml`
   - `cron/` job definition files (not its `.db`/lock/heartbeat runtime state)

   Never make `~/.hermes/` itself the private repo root. That directory also
   holds `.env` (API keys) and `auth.json` (OAuth tokens) and multiple
   sqlite DBs — the blast radius of accidentally `git add -A`-ing that root
   is a credential leak. Copying only the specific files you intend to
   version is the guardrail, not `.gitignore` alone.

## Procedure

1. **Init both repos**, rename branch to `main`, set a local (not global)
   git identity so this doesn't clash with the user's own git config:
   ```bash
   cd <repo_dir> && git init && git branch -m main
   git config user.name "Hermes Agent" && git config user.email "hermes@localhost"
   ```
2. **Write `.gitignore` before the first commit.**
   - Skills repo: exclude `.usage.json` (curator telemetry file — it
     mutates on every skill view/use and will otherwise generate commit
     noise unrelated to actual content changes), `__pycache__/`, `.venv/`
     (skills that bootstrap a Python venv for their scripts, e.g. the `pdf`
     skill, will litter one at their skill dir root).
   - Private repo: `.env`, `auth.json`, `*.db*`, `*.lock` — belt-and-suspenders
     even though you're only copying selected files in, not the live tree.
3. **Sync + commit the private repo via a copy step**, not a symlink and
   not the live files directly — see `scripts/private-config-sync.sh` for
   the copy list (memories, config.yaml, non-runtime cron files only).
4. **Automate with an event-based watcher, not a polling cron job.**
   `inotifywait` (package `inotify-tools`; `sudo apt-get install -y
   inotify-tools` if missing) reacts immediately to real changes instead of
   checking on an interval. Debounce bursts (curator/agent writes often
   touch several files in one go — a new skill is `SKILL.md` +
   `references/*` in one shot) into a single commit: drain further events
   for ~15s after the first one before committing. See
   `templates/autocommit-watcher.sh` for the full debounce loop pattern
   (works for either repo — just point `WATCH_DIR`/`REPO_DIR` at the
   skills dir directly, or at the private repo dir plus a pre-commit sync
   call for the private case).
5. **Wire it as a `systemd --user` service**, not a foreground background
   process tied to this session — it must keep running across Hermes
   restarts and reboots:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now <service-name>.service
   ```
   Template: `templates/autocommit.service`. Requires the machine to have
   `loginctl` lingering/user systemd active (already true on most systemd
   Linux hosts; check with `systemctl --user status`).
6. **Verify actual end-to-end behavior, don't assume the wiring worked:**
   append a harmless line to a tracked file, wait longer than the debounce
   window, confirm `git log --oneline -1` shows a fresh auto-commit, then
   revert the test edit and confirm the watcher commits the revert too. Only
   report success after seeing both commits land.
7. **Remote (GitHub/Gitea/etc.) is a separate, explicit decision** — don't
   add and push to a remote proactively. The skills repo in particular is a
   candidate for going public later; let the user choose destination and
   visibility rather than defaulting to push.

## Pitfalls

- Never run `git add -A` against `~/.hermes/` root itself — always scope to
  the skills dir (already secret-free) or a dedicated private-copy dir you
  populate file-by-file.
- Before trusting a private-repo commit, grep the copied `config.yaml` for
  `api_key|token|password|secret` — config.yaml is documented as
  settings-only, but verify rather than assume, especially after upstream
  Hermes changes.
- `.usage.json` in the skills dir is curator telemetry, not content — commit
  noise from it makes the history useless for tracking real skill changes.
  Gitignore it.
- Debounce is required, not optional: a single skill creation event can fire
  several filesystem events in under a second; committing per-event produces
  a fragmented, noisy history.
- Don't try to restart/stop the Hermes gateway from a `terminal` call made
  *inside* the running gateway process — SIGTERM will propagate to the
  child and kill the command before it finishes. Plain `git`/`systemctl
  --user` commands are unaffected; this only bites actual gateway restarts.
- A backgrounded watcher started via the `terminal` tool's `background=true`
  is process-scoped and dies with the session/gateway process — for
  something that must survive indefinitely, systemd user services (or cron)
  are the durable option, not a bare backgrounded shell command.
