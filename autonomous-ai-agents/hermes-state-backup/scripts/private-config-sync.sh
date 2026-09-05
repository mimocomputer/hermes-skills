#!/usr/bin/env bash
# Copies the specific Hermes files that are safe/intended to be
# version-controlled into a separate private backup repo directory.
# Deliberately allowlist-based (copy IN these files) rather than
# denylist-based (git-ignore OUT of the live ~/.hermes root) — never point
# a git repo root at ~/.hermes/ itself, it also contains .env/auth.json/DBs.
set -euo pipefail

HOME_DIR="$HOME/.hermes"
BACKUP_DIR="$HOME_DIR/private-config-backup"

mkdir -p "$BACKUP_DIR/memories" "$BACKUP_DIR/cron"

cp -f "$HOME_DIR/memories/MEMORY.md" "$BACKUP_DIR/memories/MEMORY.md" 2>/dev/null || true
cp -f "$HOME_DIR/memories/USER.md" "$BACKUP_DIR/memories/USER.md" 2>/dev/null || true
cp -f "$HOME_DIR/config.yaml" "$BACKUP_DIR/config.yaml" 2>/dev/null || true

# Cron job definitions only - skip runtime state (db, locks, heartbeats).
find "$HOME_DIR/cron" -maxdepth 1 -type f \
  ! -name '.*' ! -name '*.db' ! -name 'ticker_*' \
  -exec cp -f {} "$BACKUP_DIR/cron/" \; 2>/dev/null || true
