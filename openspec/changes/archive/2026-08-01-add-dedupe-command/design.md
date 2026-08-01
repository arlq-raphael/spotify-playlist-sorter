## Context

See proposal.md — Why. The existing tool only adds tracks; it fetches Liked Songs (`library.py`) and
plans/applies playlist membership (`sorter.py`). Dedupe needs two capabilities the code base does not
yet have: track **duration** (to distinguish exact duplicates from version pairs) and **write access to
the library** (to un-save a track). The current OAuth scope set is read-library + modify-playlists.

## Goals / Non-Goals

- Goal: a self-contained `dedupe` command whose detection logic is pure and unit-testable offline.
- Goal: never destroy data on a default run; never guess when the original is ambiguous.
- Non-Goal: fuzzy/phonetic matching, acoustic fingerprinting, or LLM assistance.
- Non-Goal: touching the `sort` command's behaviour or the genre/decade config.

## Decisions

- **Match key = normalized(title) + normalized(primary artist).** Normalization lowercases, strips
  `(feat …)`/`(with …)`, and strips trailing `- <tag>` version suffixes. Chosen over full-artist or
  album matching because collaborators and album context vary across releases of the same song.
  Alternative (ISRC) rejected: Spotify does not expose ISRC on saved-track objects here, and relinked
  duplicates can carry different ISRCs anyway.
- **Exact vs version pair by duration tolerance (±3s).** Same normalized key + duration within
  tolerance ⇒ exact duplicate (any copy kept). Beyond tolerance, or a version tag present ⇒ version
  pair. Chosen because duration is a cheap, reliable proxy for "same recording" and is already on the
  track object once we request it.
- **Keep-original policy for version pairs:** keep the untagged copy; remove the copy whose title
  carries a variant tag (remaster/live/edit/extended/remix/single/12"). Exception: a tag containing the
  word "original" marks the keeper. If neither side is clearly the original (both tagged, or two
  untagged copies with conflicting durations) → unresolved, keep both.
- **Purge from playlists:** the tool already knows how to list playlists it owns (`sorter.py`); on
  removal it will also `remove_specific_occurrences_of_items` for the removed track id from each
  genre/decade playlist that contains it. Reuses the existing playlist enumeration.
- **New module `dedupe.py`** holding pure functions (`group`, `classify`, `choose_removals`) plus a thin
  apply step that calls spotipy. Keeps the network-free logic testable like `classify.py`.
- **OAuth scope:** add `user-library-modify` to `auth.SCOPES`. Users re-authorize once (cached token is
  invalidated when scopes change; spotipy handles the re-consent prompt).

## Risks / Trade-offs

- Duration-based matching can misjudge a remaster that happens to share the original's length; mitigated
  by treating tag presence as an independent version signal and by the unresolved-keep-both fallback.
- Removing from Liked Songs is destructive; mitigated by report-only default, explicit `--apply`, and a
  printed summary of exactly what was removed. Removal is reversible by re-saving.
- Title normalization is heuristic and language-agnostic; false groupings are possible. Mitigated by
  requiring artist match too, and by never auto-removing unresolved groups.

## Open Questions

- Should `dedupe` also collapse duplicates that exist only inside playlists (not in Liked Songs)? Out of
  scope for this change; can be a follow-up once library-level dedupe is proven.
