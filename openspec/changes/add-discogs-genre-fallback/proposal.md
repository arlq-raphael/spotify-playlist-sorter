## Why

Genre classification depends entirely on Spotify's artist-level genres, which are coarse and frequently
**empty for smaller artists** — those tracks land in the "Unknown Genre" bucket. Discogs exposes
granular per-release **styles** (e.g. *Roots Reggae, Dancehall, Deep House, Nu-Jazz*) that map far more
precisely to the tool's buckets, so using it as a genre source materially improves classification.

## What Changes

- Introduce **ordered, pluggable genre providers**. A new config key `genre_providers` lists sources in
  priority order; for each track the first provider that returns a non-empty genre set wins.
- Add a **Discogs** genre provider: searches Discogs by artist + track title and returns the best
  match's `genre` + `style` values (which feed the existing bucket rules).
- Keep the **Spotify** genre provider (current behaviour) as one of the sources.
- Default order is `[discogs, spotify]` — Discogs preferred, Spotify as fallback.
- Discogs is **opt-in via a `DISCOGS_TOKEN`**: when no token is configured the Discogs provider is
  skipped (with a notice) and classification falls back to the next provider, so the tool still works
  Spotify-only with zero extra setup.
- Respect Discogs **rate limits** (60 req/min authenticated) and send the required `User-Agent`; **cache**
  lookups by artist+title so re-runs don't re-query.
- Tracks still unresolved by every provider keep the existing `no_genre_bucket` fallback.
- Non-goals: no acoustic fingerprinting, no OAuth (personal token only), no change to the decade or
  dedupe features.

## Capabilities

### New Capabilities
- `genre-providers`: an ordered set of genre sources (Spotify, Discogs) with per-track first-non-empty
  resolution, opt-in Discogs lookup (token-gated, rate-limited, cached), and graceful fallback.

### Modified Capabilities
<!-- None: genre sourcing was never spec'd; this introduces the capability additively. -->

## Impact

- New modules for the provider abstraction and the Discogs client; `cli.py`/`sorter` wiring reads
  `genre_providers` and resolves genres via the provider chain instead of calling Spotify directly.
- New optional credential `DISCOGS_TOKEN` (documented in `.env.example` / README); `config/genres.yaml`
  gains a `genre_providers` list and an optional Discogs section (user-agent, timeout).
- Uses the `requests` library (already an indirect dependency via spotipy). Tests mock `api.discogs.com`
  with the existing `responses` setup.
