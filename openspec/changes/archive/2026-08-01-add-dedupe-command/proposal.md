## Why

Spotify libraries accumulate duplicate Liked Songs: the exact same recording saved under two track
IDs (market relinks, re-adds) and near-duplicates that are alternate versions of one song (remaster,
live, radio edit, extended, remix). These bloat the library and produce duplicate entries in the
sorted playlists. Today the tool only *adds* tracks; it has no way to detect or remove these, so users
must clean up by hand.

## What Changes

- Add a new `spotify-sorter dedupe` CLI command that scans Liked Songs, groups duplicates, and reports
  them; with an opt-in flag it removes the redundant copies (keeping one per song).
- Classify each duplicate group as either an **exact duplicate** (same normalized title + primary
  artist, matching duration → same recording) or a **version pair** (same title, different
  version/duration — remaster/live/edit/etc.).
- Default behaviour is **report-only (dry-run)**; removal requires an explicit `--apply` flag.
- Duration-aware confirmation: only exact duplicates are auto-removable; version pairs are reported and
  removed only when the user opts in with a "keep original" policy (keep the untagged/earliest release,
  drop remaster/live/edit variants).
- When a removed copy also sits in sorted playlists, purge it from those playlists so no orphan remains.
- Non-goals: no fuzzy/AI matching, no cross-account dedupe, no change to the existing `sort` command's
  behaviour.

## Capabilities

### New Capabilities
- `dedupe`: detect duplicate and alternate-version tracks in the user's Liked Songs, report them
  grouped and classified, and (opt-in) remove the redundant copies while keeping one per song and
  purging removed copies from any sorted playlists.

### Modified Capabilities
<!-- None: this is additive; the existing sort behaviour is unchanged. -->

## Impact

- New CLI subcommand `dedupe` in `cli.py`; new module `dedupe.py` (grouping + policy logic).
- Reuses `library.fetch_liked_tracks` (extended to expose track duration) and the existing spotipy
  client; adds `removeUsersSavedTracks` + playlist-removal calls (new write scope already covered by
  `user-library-modify`, which must be added to the OAuth scopes).
- New unit tests for grouping/classification (no network, mirrors `test_classify.py`).
- README gains a "De-duplicate" usage section.
