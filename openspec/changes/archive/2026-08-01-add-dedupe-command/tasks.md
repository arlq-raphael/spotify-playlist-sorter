## 1. Library & auth groundwork

- [x] 1.1 Add `duration_ms` (and a `duration` helper) to `library.Track` and populate it in `fetch_liked_tracks`
- [x] 1.2 Add `user-library-modify` to `auth.SCOPES`; note the one-time re-authorization in the README

## 2. Detection logic (pure, testable)

- [x] 2.1 Create `dedupe.py` with `normalize_key(title, artist)` (lowercase, strip feat/with + version tags)
- [x] 2.2 Implement `group(tracks) -> list[list[Track]]` grouping by normalized key
- [x] 2.3 Implement `classify(group) -> "exact" | "version_pair"` using the ±3s duration tolerance and tag detection
- [x] 2.4 Implement `choose_removals(group) -> (keep_id, remove_ids, unresolved: bool)` with the keep-original policy and "original" exception

## 3. Apply step

- [x] 3.1 Implement `apply_removals(sp, sorter, removals, dry_run)` — un-save removed ids, then purge them from the owner's genre/decade playlists
- [x] 3.2 Ensure default is report-only; removal only when `--apply` is passed

## 4. CLI

- [x] 4.1 Add a `dedupe` subcommand to `cli.py` (`--apply`, `--limit`, reuse `--config` if needed)
- [x] 4.2 Print grouped report: exact duplicates, version pairs (kept/removed), and unresolved groups

## 5. Tests & docs

- [x] 5.1 Unit tests in `tests/test_dedupe.py` for normalize/group/classify/choose_removals (no network)
- [x] 5.2 Add a "De-duplicate" section to the README with `dedupe` and `dedupe --apply` examples
- [x] 5.3 Run `pytest` and `openspec validate --change add-dedupe-command --strict`
