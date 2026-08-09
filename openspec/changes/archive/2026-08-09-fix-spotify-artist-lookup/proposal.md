## Why

The Spotify genre source is dead. It fetches artist genres in batches, and Spotify removed the
batch endpoint in February 2026 — a bare 403, with no replacement offered. Because a source that
errors aborts the whole run, this does not merely reduce genre coverage: it takes `sort` down
whenever the chain reaches Spotify.

That matters more than "one source of three" suggests. Spotify is the only source needing no
credential beyond the app itself, so it is the floor the other two fall through to. Measured
against a real 1853-track library, the exact ISRC source resolves **48%**, leaving roughly 964
tracks with nowhere else to go unless a Discogs token is configured.

## What Changes

- Look artists up individually instead of in batches. The single-artist endpoint still works.
- Cache artist genres persistently, keyed by artist. The source currently does not use the cache
  at all — tolerable at 27 batched requests per run, wasteful at 1333 individual ones.
- **Not changed**: provider order, the fallthrough contract, or what the source returns for a
  given artist.

## Measurements, because the first estimate was wrong

The issue originally judged per-artist lookups "severe — up to a 50× increase in requests, rate
limiting becomes a live concern." Measured, that is not the case:

| | Measured |
|---|---|
| Distinct artists in the library | 1333 (from 2557 references) |
| Per-artist lookup | 0.11s each, 20/20 clean → **~2.4 min** for the whole library |
| Batched (what was removed) | 27 requests |
| The ISRC source, for comparison | 5.0s per track, 48% hit rate → **~154 min** cold |

So the "expensive" replacement is roughly **60× cheaper than the source that already runs first**,
and no rate limiting appeared at that volume. Dropping the Spotify source instead would strand
over half the library to save two and a half minutes.

## Capabilities

### New Capabilities
<!-- None. This fixes an existing capability. -->

### Modified Capabilities
- `genre-providers`: two requirements. The Spotify source currently specifies that genres are
  "fetched in batches", which the platform no longer permits. The caching requirement enumerates
  its key types as "(ISRC, or artist+title)", which does not cover artist lookups.

## Out of scope

**Provider order.** The measurements invite an obvious question: the chain runs
`musicbrainz → discogs → spotify` on the principle that exact ISRC identification is preferable,
yet the exact source costs 154 minutes for 48% coverage while the coarse one costs 2.4 minutes.
That is a real trade between precision and cost, and it deserves its own decision rather than
being smuggled into a bug fix. The order is configurable, so anyone feeling the cost can already
change it.

## Impact

- **Code**: the artist-genre fetch, plus wiring the Spotify source into the existing cache.
- **Tests**: the double models the removed batch endpoint and must move to per-artist responses.
- **Runtime**: a cold first run gains ~2.4 minutes on the Spotify stage; subsequent runs pay
  almost nothing, because artist genres are then cached.
- **Not fixed here**: the behavior that turns any source error into an aborted run. This removes
  today's error, not the fragility.
