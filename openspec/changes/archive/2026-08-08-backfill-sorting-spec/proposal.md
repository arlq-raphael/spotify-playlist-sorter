## Why

`sort` is the tool's primary command, and it is the only major capability with no spec.
`openspec/specs/` covers `config-loading`, `config-setup`, `credentials`, `dedupe`, and
`genre-providers`, but nothing describes how a liked track becomes a playlist placement —
bucket matching, decade derivation, dimension selection, or the idempotency guarantee that
makes the command safe to re-run. That behavior predates the adoption of OpenSpec, so it
was never captured.

This matters now because the proposed Go port (#8) depends on having language-agnostic
acceptance criteria to port *against*. The other five specs already serve that purpose and
would transfer untouched; sorting is the one place where the safety net is missing. The
spec must be written while the current implementation is still the source of truth, so each
scenario can be checked against a passing test suite as it is drafted — not reconstructed
from the new implementation afterwards, which would defeat the point.

## What Changes

- Add a `sorting` capability spec documenting the behavior that already exists: Liked Songs
  ingestion, genre and decade classification, dimension selection, plan construction,
  idempotent application, and dry-run.
- Document behavior in implementation-neutral terms (no language, library, or module names),
  so the spec is directly reusable as the acceptance contract for #8.
- **No behavior changes and no source changes.** This is a documentation backfill. If
  drafting surfaces something that looks like a defect, it is filed separately rather than
  fixed here.

Explicitly out of scope, because existing specs already cover them:

- Genre *resolution* from external sources → `genre-providers`
- Config discovery, layering, and precedence → `config-loading`
- Duplicate detection and removal → `dedupe`

## Capabilities

### New Capabilities
- `sorting`: How liked tracks are read, classified into genre and decade buckets, planned
  into target playlists, and applied idempotently — including dry-run and the ownership
  rule for matching existing playlists.

### Modified Capabilities
<!-- None. This change documents existing behavior; no existing requirement changes. -->

## Impact

- **Specs**: adds `openspec/specs/sorting/spec.md` on archive. No existing spec is modified.
- **Code**: none. No file under `src/` or `tests/` is touched by this change.
- **Verification**: relies on the existing suite (`tests/test_sorter.py`,
  `tests/test_classify.py`, `tests/test_library.py`, `tests/test_cli.py`) as evidence that
  the documented scenarios match reality; the suite must pass unchanged.
- **Downstream**: unblocks #8 by supplying the missing acceptance criteria for the core
  command. Also gives the `configure` wizard and README a single authority to cite for
  bucket-matching and idempotency semantics.
