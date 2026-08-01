## Context

See proposal.md — Why. Today `cli.cmd_sort` calls `library.fetch_artist_genres` + `attach_genres`
directly, then classifies. This change inserts a provider layer between "fetch" and "classify" so the
genre source is pluggable and ordered. Discogs data lives on releases (`genre` broad + `style`
granular); its API needs a token, a `User-Agent`, and 60 req/min pacing.

## Goals / Non-Goals

- Goal: a clean `GenreProvider` seam with Spotify, Discogs, and an ISRC-exact (MusicBrainz)
  implementation, resolved in config order.
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
- **ISRC on the model:** `library.Track` gains `isrc` (from `external_ids.isrc`), populated in
  `fetch_liked_tracks`. Some tracks lack an ISRC, so a text fallback is always kept.
- **ISRC lookup goes through MusicBrainz, not Discogs.** Discogs' `/database/search` has **no
  first-class ISRC filter**, so ISRC there is unreliable. MusicBrainz exposes a direct endpoint —
  `GET /ws/2/isrc/{isrc}?inc=genres+tags&fmt=json` — returning the exact recording plus its community
  genre tags. So the effective order is: **ISRC → MusicBrainz (exact)** → **Discogs (artist+title, for
  granular styles)** → **Spotify (artist genres)**. This keeps ISRC precise while still using Discogs
  styles for non-ISRC tracks. MusicBrainz is free but requires a `User-Agent` and **1 req/sec** pacing;
  it is cached like Discogs.
- **Discogs text query:** `GET /database/search?type=release&artist=<a>&track=<t>&token=<tok>`, take the
  first result's `genre` + `style`, lowercased + deduped. `track` chosen over `release_title` (we match
  songs, not albums); best-hit only, misses fall through.
- **Grouping via Discogs' two levels:** the Discogs provider returns both the broad `genre` and the
  granular `style`. Because Discogs `genre` is itself a coarse parent (e.g. *Deep House* is a style of
  *Electronic*), it provides reliable top-level grouping straight from the data. So bucket rules can lean
  on the broad `genre` for the "bigger genre" and treat `style` as optional refinement when the config
  defines finer buckets — reducing reliance on hand-written substring rules. Both values are returned;
  the ordered bucket config decides which wins. (A richer default style→bucket mapping seeded from the
  Discogs/MusicBrainz taxonomy is tracked as a follow-up, out of scope here.)
- **Why not acoustic fingerprinting:** it needs audio Spotify no longer exposes (previews removed
  2024-11) and would re-identify tracks whose identity we already have — ISRC delivers the precision at
  ~zero cost. (See proposal.md.)
- **Rate limiting:** a small token-bucket/sleep keeping ≤ ~1 req/sec; on HTTP 429 honour `Retry-After`
  (and `X-Discogs-Ratelimit-Remaining`). Discogs personal-token limit is 60/min.
- **Caching:** in-memory dict keyed by normalized `artist|title`; optionally persisted to a JSON file
  (`.discogs-cache.json`, git-ignored) so re-runs are instant. Cache stores the resolved genre list
  (including empty, to avoid re-querying known misses).
- **User-Agent:** required by Discogs (403 otherwise) — send `spotify-playlist-sorter/<version>
  (+github url)`.
- **Config:** `genre_providers: [musicbrainz, discogs, spotify]` (order matters; `musicbrainz` is the
  ISRC-exact source). Unknown names error early. A provider named `discogs` with no `DISCOGS_TOKEN`
  prints a notice and is skipped; `musicbrainz` needs no token.
- **Clients:** Discogs via the maintained **`python3-discogs-client`** SDK (import `discogs_client`) — it
  handles token auth, `User-Agent`, and rate limiting, and exposes `search(...)` with `genre`/`style`.
  MusicBrainz is **hand-rolled on `requests`** (a single ISRC endpoint; the standard SDK `musicbrainzngs`
  uses `urllib`, which our `responses` HTTP-level tests cannot intercept — not worth the fidelity loss
  for one GET). Both paths ultimately use `requests`, so `responses` mocking stays uniform across tests.
  Net dependency change: `+python3-discogs-client` (MusicBrainz adds none; `requests` is already present).

## Risks / Trade-offs

- **Speed:** Discogs-first queries every track (60/min, no batch) — a large first run is slow; mitigated
  by caching and by keeping Spotify-first available via config. Documented clearly.
- **Match ambiguity:** artist+title search can hit the wrong release; mitigated by using broad
  genre/style → bucket matching and by the "no match → fall through" path.
- **Extra credential + external dependency** (Discogs uptime); mitigated by opt-in + graceful skip.

## Open Questions

- Persist the cache across runs by default, or keep it in-memory only? Leaning persisted JSON (git-ignored)
  since Discogs-first benefits most from it; revisit if it complicates testing.
