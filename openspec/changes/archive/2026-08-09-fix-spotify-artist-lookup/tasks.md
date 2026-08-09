Every task here closes before merge. Nothing is deferred past it — work that cannot be finished
in this change belongs in an issue, and filing that issue is itself a task below.

## 1. Make the test double match the platform

Tighten the double first, so the existing Spotify-source tests go red against the endpoint that no
longer exists before any source change. If they stay green after 1.2, the double is still serving
a removed endpoint.

- [x] 1.1 Serve single-artist lookups
- [x] 1.2 Stop serving the batch endpoint — a request for it should fail the way the platform
      fails it, so nothing can quietly depend on batching again
      → answers 403. Registration order matters: the batch pattern must precede the
      single-artist one, or `/artists?ids=` matches `/artists/{id}` and quietly succeeds
- [x] 1.3 Confirm the existing tests fail, and fail for that reason
      → 4 went red with `SpotifyException`

## 2. Replace the batch fetch

- [x] 2.1 Look up each distinct artist individually
- [x] 2.2 De-duplicate within a run: one lookup per artist however many tracks credit it
      → 5 tracks sharing an artist make 1 lookup
- [x] 2.3 Preserve what the source returns — genres combined across a track's artists, in credit
      order, without repeats, lower-cased as every source must be

## 3. Cache artist lookups

- [x] 3.1 Wire the Spotify source into the existing persistent cache, keyed by artist and
      namespaced so it cannot collide with the recording and artist+title keys already stored
      → key is `sp:artist:<id>`
- [x] 3.2 Cache empty results too — an artist with no genres should not be re-queried next run
- [x] 3.3 Confirm a second run over the same library makes no artist requests
      → confirmed by test and by the live run

## 4. Failure behavior

Decided in design.md, not here: a failing artist lookup skips that artist and the run continues,
and failures are reported once rather than swallowed. Inheriting "any error kills the run" would
have multiplied the blast radius of #18 by 49 as a direct result of this change.

- [x] 4.1 A failing artist lookup skips that artist; the run continues and the track still
      receives genres from its other artists
- [x] 4.2 Failures are surfaced once, so a permanently broken source cannot look like one that
      simply never matches
- [x] 4.3 Both covered by tests
      → the catch is narrowed to `SpotifyException` and `RequestException`, not bare
      `Exception`, so our own parsing bugs cannot be reported as "artist had no genres"
      (ruff BLE001 caught the first attempt)

## 5. Verify

- [x] 5.1 Full suite passes, coverage above the floor
      → 115 passed (was 109), 98.94%
- [x] 5.2 `ruff check src tests` clean
- [x] 5.3 `openspec validate fix-spotify-artist-lookup --strict` passes
- [x] 5.4 Verified live with a **dry run** against the real API. Sufficient here, unlike for the
      playlist-creation fix: genre resolution happens before anything branches on dry-run, so a
      dry run exercises the fixed path identically to a real one and writes nothing. Use a small
      `--limit` — a full-library genre run is dominated by the ISRC source at roughly 154
      minutes, which this change does not touch
      → `--limit 12 -d genre` resolved 12 tracks into 7 buckets, no 403, no crash. First
      successful genre run since the endpoint was removed
- [x] 5.5 Measure the cold and cached cost of the Spotify stage, so the proposal's numbers are
      confirmed rather than extrapolated from a 20-request sample
      → cold 68s for 12 tracks, warm **1.2s** (57×). Cache held 17 entries — 12 recording
      keys, 5 artist keys — 8 of them empty misses. The cold time is dominated by the ISRC
      source, which this change does not touch

## 6. Record what this change deliberately leaves out

- [x] 6.1 File the provider-order question as its own issue: the exact source costs ~154 min for
      48% coverage, the coarse one ~2.4 min. Out of scope here, but it must exist somewhere other
      than a merged commit message
      → filed as #28, with options and no recommendation; caching makes the cost one-time,
      which weakens the case for reordering
- [x] 6.2 Re-read #18 against the code as it stands after this change and confirm it still
      describes the behavior accurately — comment on it either way, since this change alters how
      often that path is reachable
      → commented. Still holds for MusicBrainz and Discogs, no longer for Spotify. That
      asymmetry is arguably worse than the original state and argues for fixing it uniformly
      at the resolution level rather than per source

## 7. Found while implementing, not planned

- [x] 7.1 **Test isolation gap, fixed here.** Wiring the Spotify source into the cache exposed
      that the genre cache resolves against the working directory, so CLI tests wrote
      `.genre-cache.json` into the repo root and read back what an earlier test left there. It
      caused a real cross-test failure — one test's artist genres decided another test's
      playlist. `conftest.py` now redirects the cache per test via `SPOTIFY_SORTER_CONFIG`.
      The XDG user-config path does not work for this: pre-creating a user config makes
      `configure` refuse to overwrite and breaks its own tests
