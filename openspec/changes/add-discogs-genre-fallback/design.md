## Context

See proposal.md — Why. Today `cli.cmd_sort` calls `library.fetch_artist_genres` + `attach_genres`
directly, then classifies. This change inserts a provider layer between "fetch" and "classify" so the
genre source is pluggable and ordered. Discogs data lives on releases (`genre` broad + `style`
granular); its API needs a token, a `User-Agent`, and 60 req/min pacing.

## Goals / Non-Goals

- Goal: a clean `GenreProvider` seam with Spotify + Discogs implementations, resolved in config order.
- Goal: Discogs strictly optional — no token means no behaviour change vs today.
- Non-Goal: OAuth, acoustic matching, or per-release disambiguation beyond "best search hit".

## Decisions

- **Provider interface:** `GenreProvider.genres_for(tracks) -> dict[track_id, list[str]]`, returning
  genres only for tracks it could resolve. A batch signature lets the Spotify provider keep its 50-artist
  batching while the Discogs provider iterates internally. Chosen over a per-track interface so Spotify
  stays fast.
- **Resolution:** `resolve_genres(tracks, providers)` walks providers in order, asking each only for the
  tracks still unresolved, and stops a track once any provider returns a non-empty list. First-non-empty,
  not merge — keeps buckets deterministic and avoids mixing vocabularies.
- **Discogs query:** `GET /database/search?type=release&artist=<a>&track=<t>&token=<tok>`, take the first
  result's `genre` + `style`, lowercased, deduped. `track` search chosen over `release_title` because we
  match songs, not albums. Best-hit only (no scoring) — good enough given the buckets are broad; misses
  fall through to Spotify.
- **Rate limiting:** a small token-bucket/sleep keeping ≤ ~1 req/sec; on HTTP 429 honour `Retry-After`
  (and `X-Discogs-Ratelimit-Remaining`). Discogs personal-token limit is 60/min.
- **Caching:** in-memory dict keyed by normalized `artist|title`; optionally persisted to a JSON file
  (`.discogs-cache.json`, git-ignored) so re-runs are instant. Cache stores the resolved genre list
  (including empty, to avoid re-querying known misses).
- **User-Agent:** required by Discogs (403 otherwise) — send `spotify-playlist-sorter/<version>
  (+github url)`.
- **Config:** `genre_providers: [discogs, spotify]` (order matters). Unknown names error early. A
  provider named `discogs` with no `DISCOGS_TOKEN` prints a notice and is skipped.
- **HTTP client:** use `requests` directly (already present via spotipy) rather than adding a dep.

## Risks / Trade-offs

- **Speed:** Discogs-first queries every track (60/min, no batch) — a large first run is slow; mitigated
  by caching and by keeping Spotify-first available via config. Documented clearly.
- **Match ambiguity:** artist+title search can hit the wrong release; mitigated by using broad
  genre/style → bucket matching and by the "no match → fall through" path.
- **Extra credential + external dependency** (Discogs uptime); mitigated by opt-in + graceful skip.

## Open Questions

- Persist the cache across runs by default, or keep it in-memory only? Leaning persisted JSON (git-ignored)
  since Discogs-first benefits most from it; revisit if it complicates testing.
