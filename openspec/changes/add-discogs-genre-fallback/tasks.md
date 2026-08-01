## 1. Config & provider seam

- [ ] 1.1 Add `genre_providers` (default `["musicbrainz", "discogs", "spotify"]`) + optional `discogs`/`musicbrainz` sections to `config/genres.yaml` and `Config`
- [ ] 1.2 Define a `GenreProvider` protocol (`genres_for(tracks) -> dict[track_id, list[str]]`) in a new `providers.py`
- [ ] 1.3 Implement `resolve_genres(tracks, providers)` — walk providers in order, first non-empty wins, only ask each for still-unresolved tracks

## 2. Track model & Spotify provider

- [ ] 2.1 Add `isrc` to `library.Track` (from `external_ids.isrc`), populated in `fetch_liked_tracks`
- [ ] 2.2 Wrap the existing batched artist-genre fetch as `SpotifyGenreProvider`

## 3. ISRC-first via MusicBrainz

- [ ] 3.1 Add a `musicbrainz.py` client: `genres_for_isrc(isrc) -> list[str]` (`GET /ws/2/isrc/{isrc}?inc=genres+tags&fmt=json`), required `User-Agent`, pace to 1 req/sec, honour 503/`Retry-After`
- [ ] 3.2 `MusicBrainzGenreProvider`: resolve tracks that have an ISRC; skip those without one

## 4. Discogs provider

- [ ] 4.1 Add a `discogs.py` client: `search(artist, title) -> list[str]` (genre + style), required `User-Agent`, `token` from `DISCOGS_TOKEN`
- [ ] 4.2 Rate limiting: pace to ≤60/min; on 429 honour `Retry-After` / `X-Discogs-Ratelimit`
- [ ] 4.3 Cache external lookups by key (ISRC, or normalized `artist|title`) — in-memory + optional git-ignored JSON persist; cache misses too
- [ ] 4.4 `DiscogsGenreProvider`: skip with a notice when no token; return empty on no match

## 5. Wiring

- [ ] 5.1 Build the provider chain from config in `cmd_sort` and resolve genres via `resolve_genres` instead of calling Spotify directly
- [ ] 5.2 Unknown provider name errors early; `.env.example` gains `DISCOGS_TOKEN`

## 6. Tests & docs

- [ ] 6.1 Extend the `responses` mock for `musicbrainz.org/ws/2/isrc/...` and `api.discogs.com/database/search`
- [ ] 6.2 Tests: provider order/first-non-empty, ISRC→genres, ISRC no-result → fall-through, no-ISRC skip, Discogs match → styles, no-token skip, caching (queried once), rate-limit retry
- [ ] 6.3 README: "Genre sources" section (ISRC→MusicBrainz → Discogs → Spotify order, Discogs token setup, speed trade-off)
- [ ] 6.4 Run `pytest` (keep coverage ≥ floor) and `openspec validate add-discogs-genre-fallback --strict`
