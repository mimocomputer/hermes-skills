#!/usr/bin/env bash
# Generic debounced inotify -> git auto-commit watcher template.
# Copy and adapt WATCH_DIRS / REPO_DIR / (optional) sync step per use case.
#
# For a repo that IS the watched dir (e.g. the skills dir itself):
#   WATCH_DIRS=("$REPO_DIR"), no pre-commit sync needed.
# For a repo that holds COPIES of files living elsewhere (e.g. a private
# memories/config backup), set WATCH_DIRS to the real source paths and add
# a sync_files() step that copies them into REPO_DIR before committing.
set -euo pipefail

REPO_DIR="$HOME/.hermes/CHANGE_ME"
WATCH_DIRS=("$REPO_DIR")
DEBOUNCE_SECS=15

sync_files() {
  # Override / extend this if REPO_DIR holds copies rather than being the
  # live source directory. Example:
  #   cp -f "$HOME/.hermes/memories/MEMORY.md" "$REPO_DIR/memories/MEMORY.md"
  :
}

commit_if_dirty() {
  sync_files
  cd "$REPO_DIR"
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    local summary
    summary=$(git status --porcelain | awk '{print $1}' | sort | uniq -c | tr '\n' ' ')
    git commit -m "Auto-commit: changed ($summary) $(date -Iseconds)" >/dev/null
    echo "$(date -Iseconds) committed: $summary"
  fi
}

# Catch up on anything that changed while the watcher was down.
commit_if_dirty

inotifywait -m -r -e create,modify,delete,move \
  --exclude '(\.git/|\.usage\.json$|__pycache__|\.venv/)' \
  "${WATCH_DIRS[@]}" |
while read -r _dir _events _file; do
  # Drain further events for DEBOUNCE_SECS so a burst of writes (e.g. a new
  # skill = SKILL.md + references/* in one shot) becomes one commit.
  while read -r -t "$DEBOUNCE_SECS" _dir2 _events2 _file2; do :; done
  commit_if_dirty
done
