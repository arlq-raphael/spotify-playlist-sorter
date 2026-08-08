## 1. Verify each requirement against the current implementation

Each task is done when every scenario in that requirement has been confirmed against the code
and against evidence — an existing test where one covers it, or a direct probe where none does.
Any mismatch is a wording fix in the spec or a new issue, never a source change in this change.

- [x] 1.1 "Read the saved library" — pagination (`test_fetch_liked_tracks_paginates_and_parses`,
      120 tracks), `--limit` and id-less entries
      (`test_fetch_liked_tracks_skips_local_and_respects_limit`), date parsing
      (`test_year_from_release_date`). Probe found `"19"` yields year `19`, so the scenario was
      reworded from "four-digit year" to "leading characters cannot be read as a year"
- [x] 1.2 "Ordered, first-match-wins genre buckets" — `test_genre_first_match_wins_order`,
      `test_genre_substring_matching`
- [x] 1.3 "Genre fallbacks" — `test_genre_fallbacks` covers both buckets; disabling either is
      untested, probed directly and confirmed to yield no placement
- [x] 1.4 "Decade bucket" — `test_decade` covers naming, no-year, and the floor clamp; the
      no-floor case is untested, probed directly (1935 → `1930s`, 1940 → `1940s`)
- [x] 1.5 "Dimension selection" — `test_plan_places_by_genre_and_decade`, `test_cli_sort_applies`,
      `test_build_classifiers_unknown_dimension_exits`,
      `test_build_classifiers_respects_decades_disabled`. That both failures occur before any
      write is structural: classifier construction precedes planning and applying
- [x] 1.6 "Plan before changing anything" — de-duplication
      (`test_plan_add_dedupes_within_playlist`), skip recording and reporting
      (`test_plan_records_skips`, `test_cli_sort_decade_only_reports_skips`); prefix application
      is untested, probed directly
- [x] 1.7 "Apply idempotently" — create-then-idempotent (`test_apply_creates_then_is_idempotent`),
      pagination past one page of playlists and of items
      (`test_existing_playlists_paginates_over_50`, `test_playlist_track_ids_paginates_over_100`).
      Two gaps probed directly: a partial delta (playlist holding 2 of 4 planned tracks added
      exactly the 2 missing, leaving the others untouched) and an add larger than one request
      permits (250 tracks all stored, no duplicates). Visibility-from-config is verified by code
      reading only — the test mock discards the field
- [x] 1.8 "Only match playlists the user owns" — `test_existing_playlists_excludes_other_owners`
      covers the lookup; the full apply path is untested, probed directly and confirmed to create
      the user's own playlist and leave the foreign-owned one unchanged
- [x] 1.9 "Dry run changes nothing" — `test_apply_dry_run_changes_nothing`,
      `test_apply_dry_run_add_to_existing_playlist`

## 2. Confirm the spec is implementation-neutral

- [x] 2.1 Searched the delta for module, function, type, library, and language names — zero hits
- [x] 2.2 Every scenario is a testable WHEN/THEN
- [x] 2.3 No requirement strays into `genre-providers`, `config-loading`, or `dedupe` territory

## 3. Validate and check for regressions

- [x] 3.1 `openspec validate backfill-sorting-spec --strict` passes
- [x] 3.2 Suite passes unchanged (99 passed, 98.71% coverage); `git status` shows no modification
      under `src/` or `tests/`

## 4. Follow-ups

- [x] 4.1 Filed #10 — the decade floor rewrites the year rather than routing to a catch-all, so a
      1935 track is filed under `1950s`. Documented as-is here; the floor scenario needs updating
      if #10 is fixed
- [x] 4.2 Genre matching does not fold case — case-insensitivity is an invariant every source
      maintains independently by lower-casing on ingest. Captured as its own requirement in the
      delta rather than left implicit, since a source that skips normalization misfiles silently
      into the unmatched bucket with no error. No live defect: all three current sources normalize
- [x] 4.3 Commented on #8 recording that `openspec/config.yaml`'s `context:` block describes the
      current stack, is injected into every generated artifact, and must be rewritten before any
      port artifacts are generated
