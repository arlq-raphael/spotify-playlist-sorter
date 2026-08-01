## 1. Config & provider seam

- [ ] 1.1 Add `genre_providers` (default `["discogs", "spotify"]`) + optional `discogs` section to `config/genres.yaml` and `Config`
- [ ] 1.2 Define a `GenreProvider` protocol (`genres_for(tracks) -> dict[track_id, list[str]]`) in a new `providers.py`
- [ ] 1.3 Implement `resolve_genres(tracks, providers)` — walk providers in order, first non-empty wins, only ask each for still-unresolved tracks

## 2. Spotify provider

- [ ] 2.1 Wrap the existing batched artist-genre fetch as `SpotifyGenreProvider`

## 3. Discogs provider

- [ ] 3.1 Add a `discogs.py` client: `search(artist, title) -> list[str]` (genre + style), required `User-Agent`, `token` from `DISCOGS_TOKEN`
- [ ] 3.2 Rate limiting: pace to ≤60/min; on 429 honour `Retry-After` / `X-Discogs-Ratelimit`
- [ ] 3.3 Cache by normalized `artist|title` (in-memory + optional git-ignored JSON persist), caching misses too
- [ ] 3.4 `DiscogsGenreProvider`: skip with a notice when no token; return empty on no match

## 4. Wiring

- [ ] 4.1 Build the provider chain from config in `cmd_sort` and resolve genres via `resolve_genres` instead of calling Spotify directly
- [ ] 4.2 Unknown provider name errors early; `.env.example` gains `DISCOGS_TOKEN`

## 5. Tests & docs

- [ ] 5.1 Extend the `responses` mock (or add one) for `api.discogs.com/database/search`
- [ ] 5.2 Tests: provider order/first-non-empty, Discogs match → styles, no-match fall-through, no-token skip, caching (queried once), rate-limit retry
- [ ] 5.3 README: "Genre sources" section (Discogs-first default, token setup, speed trade-off vs Spotify-first)
- [ ] 5.4 Run `pytest` (keep coverage ≥ floor) and `openspec validate add-discogs-genre-fallback --strict`
