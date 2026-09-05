---
name: sqlite-corruption-recovery
description: Use when SQLite is malformed or integrity_check fails.
---

# SQLite Corruption Recovery

## When to use
- App/tool reports "database disk image is malformed" or similar SQLite error.
- `PRAGMA integrity_check` returns non-"ok" output (btree errors, "2nd reference to page N", "wrong # of entries in index").
- You need to salvage as much real data as possible into a fresh, valid database file.

## Core pitfall (the one that will burn you)
On a corrupted file, **a plain full-table scan (`SELECT * FROM table`) can silently walk over corrupted/duplicated B-tree pages and fabricate phantom rows** — typically mostly-NULL rows that don't correspond to any real record. This happened in practice: a broken `state.db` had 6 real sessions, but `SELECT * FROM sessions` (or a `.recover` dump swallowed into a fresh DB) produced 19 extra NULL-filled phantom rows, and `.recover` itself *dropped* 3 of the 6 real sessions entirely.

**Fix:** route the read through an *intact index* instead of a raw heap scan — add `ORDER BY <indexed_column>` (e.g. `ORDER BY started_at`, `ORDER BY id`) to force SQLite to use the corresponding index rather than scanning table pages directly. This alone eliminated the phantom rows and recovered all 6 real sessions correctly. Verify row counts before and after with plain vs. indexed queries — if a bare `SELECT count(*)` disagrees with what you get after `ORDER BY`, that's the tell.

## Procedure
1. **Diagnose first.** `sqlite3 broken.db "PRAGMA integrity_check;"` — read every line, don't just check exit code. Note which tables/indexes are implicated.
2. **Try `.recover` but don't trust it blindly.** `sqlite3 broken.db ".recover" > dump.sql` reconstructs a best-effort SQL dump, and any truly-unreachable rows land in a synthetic `lost_and_found` table. It errors on system tables (`sqlite_sequence`, `sqlite_master` — expected, ignore) but can also *lose whole rows* it should have found. Cross-check its row counts against step 3.
3. **Prefer targeted, indexed exports for tables you care about** (safer than `.recover` when you know the schema):
   - Copy the CURRENT/expected schema from a known-good sibling DB if one exists: `sqlite3 good.db ".schema" > schema.sql`.
   - Build a fresh DB from that schema: `sqlite3 new.db < schema.sql` (ignore "reserved for internal use" errors on FTS shadow tables / sqlite_sequence — those are auto-created).
   - Export each real table from the broken DB via an INDEXED query, not a bare scan:
     `sqlite3 broken.db ".mode insert sessions" "SELECT * FROM sessions ORDER BY started_at;" > sessions.sql`
   - Import into the fresh DB: `sqlite3 new.db < sessions.sql`.
   - Do NOT use `ATTACH DATABASE broken.db AS broken; INSERT INTO x SELECT * FROM broken.x` — in practice this reproduced the same corruption-driven duplication bug. Export to a `.sql` file with the `.mode insert` + `ORDER BY` trick and import that instead.
4. **Rebuild derived structures after import:**
   - FTS tables: `INSERT INTO messages_fts(messages_fts) VALUES('rebuild');`
   - `REINDEX; ANALYZE; VACUUM;`
5. **Verify before declaring success:**
   - `PRAGMA integrity_check;` must return exactly `ok`.
   - Row counts per table should match your independently-verified expected counts (e.g. from the original error report, or a `COUNT(*)` via the indexed query in step 3, not a raw scan on the broken file).
   - Spot-check a full-text or business-logic query (e.g. an FTS MATCH) to confirm the rebuilt indexes actually work, not just that the table exists.
6. **Never overwrite the live/original file directly.** Build the recovered copy at a separate path; let the user swap it in once the source service is stopped (avoids a live WAL/SHM clobbering your recovery).

## Pitfalls
- Corrupted-page symptoms (duplicate page references, "never used" pages) mean a raw scan is not a reliable source of truth — always sanity-check against an indexed read.
- `.recover`'s row counts can be *lower* than reality; a manual indexed export can be more complete. Compare both.
- Stray `-wal`/`-shm` files next to the target path can clobber a manually-placed recovered DB on next open — remove/rename them before swapping in a recovered file.
