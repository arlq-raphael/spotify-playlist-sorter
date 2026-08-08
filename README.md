# spotify-playlist-sorter

[![CI](https://github.com/arlq-raphael/spotify-playlist-sorter/actions/workflows/ci.yml/badge.svg)](https://github.com/arlq-raphael/spotify-playlist-sorter/actions/workflows/ci.yml)

Sort your Spotify **Liked Songs** into tidy per-**genre** and per-**decade** playlists — automatically,
and idempotently (re-run any time to file only what's new).

Classification is deterministic: it resolves each track's **genre** from an ordered chain of sources
(MusicBrainz by ISRC → Discogs → the artist's Spotify genres) and its **decade** from the album release
year, then maps them to bucket playlists via editable rules. No LLM; the default chain needs no extra
API keys beyond your Spotify app credentials (Discogs is optional).

```
Liked Songs ──► [ genre buckets ]   Reggae Roots & Dub, Hip-Hop / Rap, House / Electro, Jazz, …
            └─► [ decade buckets ]  1960s, 1970s, 1980s, 1990s, 2000s, 2010s, 2020s
```

## Install

```bash
git clone https://github.com/arlq-raphael/spotify-playlist-sorter
cd spotify-playlist-sorter
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Set up Spotify credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → **Create app**.
2. In the app's settings, add this exact **Redirect URI**: `http://127.0.0.1:8888/callback`
3. Copy your **Client ID** and **Client Secret**, then run the setup wizard:

```bash
spotify-sorter configure
```

`configure` walks you through your preferences and (optionally) your Spotify Client
ID/Secret and Discogs token, saving **secrets** to `~/.config/spotify-sorter/credentials`
(mode `600`) and **preferences** to `~/.config/spotify-sorter/config.yaml`. Prefer env
vars? `cp .env.example .env` and fill in `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET`
instead — both work (see [Configuration](#configuration)).

First run opens a browser to authorize; the token is cached in `.cache` (git-ignored).

## Usage

```bash
# Preview everything first — changes nothing:
spotify-sorter sort --dry-run

# Sort by both genre and decade (the default):
spotify-sorter sort

# Only one dimension, or a subset:
spotify-sorter sort --dimensions genre
spotify-sorter sort -d decade

# Try it on just your 50 most-recent likes:
spotify-sorter sort --limit 50 --dry-run
```

Re-run it whenever you add new likes — existing playlists are matched by name and only missing tracks
are added.

## De-duplicate your Liked Songs

Libraries accumulate duplicates — the same recording saved twice, or several versions of one song
(remaster / live / edit / remix). The `dedupe` command finds them and can remove the redundant copies.

```bash
# Report only (default) — changes nothing:
spotify-sorter dedupe

# Actually remove the redundant copies:
spotify-sorter dedupe --apply
```

It reports three groups:
- **Exact duplicates** — same recording (matching title, artist, and duration); one copy is kept.
- **Version pairs** — same song, different version; the **original** is kept and the tagged variant
  (remaster/live/edit/…) removed. A tag literally saying "Original …" is treated as the keeper.
- **Unresolved** — when the original can't be determined (both tagged, or conflicting durations); **both
  are kept** and reported, never guessed.

When a copy is removed it's also purged from any genre/decade playlists it was in, so no orphan remains.

> `dedupe` needs the `user-library-modify` scope. If you authorized an earlier version, delete `.cache`
> and re-run once to re-consent.

## Configuration

The tool ships with a sensible **default config** bundled inside the package, so it works
out of the box. To customize, you don't edit that file — you layer your own settings on
top. Configuration is assembled from these layers, **each overriding the one before it**
(a partial file only changes the keys it sets, inheriting the rest):

1. the **bundled default**,
2. `~/.config/spotify-sorter/config.yaml` — your persistent config (honors `$XDG_CONFIG_HOME`),
3. `$SPOTIFY_SORTER_CONFIG` — a config file named by that env var,
4. `--config <path>` — a config file for a single run.

Run `spotify-sorter configure` to generate your `config.yaml` interactively (it writes
only what you change). Or copy the default from
[`src/spotify_sorter/data/genres.yaml`](src/spotify_sorter/data/genres.yaml) and edit a copy.

**Secrets** live separately, in `~/.config/spotify-sorter/credentials` (mode `600`), as
`KEY=VALUE` lines — `DISCOGS_TOKEN`, and optionally `SPOTIPY_CLIENT_ID` /
`SPOTIPY_CLIENT_SECRET` / `SPOTIPY_REDIRECT_URI`. They're loaded at startup with precedence
**environment → project `./.env` → credentials file**, so an exported env var or a local
`.env` always wins for a one-off. Secrets are never written into `config.yaml`.

## How genre classification works

For each track, the tool collects the genres of its artists (see [Genre sources](#genre-sources))
and walks the `genre_buckets` list **top to bottom**, choosing the **first** bucket whose any `match`
substring appears in any of those genres. **Order = priority**, so more specific buckets go above
generic ones (e.g. `Ragga / Dancehall` before `Reggae Roots & Dub`, so a *dancehall* track lands in
Ragga).

Add your own `genre_buckets` to your `config.yaml` to rename buckets, reorder priorities, or add new
ones — for example:

```yaml
genre_buckets:
  - name: "French Rap"
    match: [french hip hop, rap francais]
  - name: "Hip-Hop / Rap"
    match: [hip hop, rap, trap, drill]
```

Options in the same file control fallbacks (`unmatched_genre_bucket`, `no_genre_bucket`), a playlist
name `prefix`, public/private playlists, and the decade `floor` — all settable via `configure`.

> **Note:** Spotify returns genres per *artist*, not per track, and smaller artists often have none —
> those land in the `no_genre_bucket` ("Unknown Genre") so nothing is silently dropped.

## Genre sources

Genres are resolved from an **ordered chain of sources** (`genre_providers` in your config);
the first source with a hit for a track wins:

1. **MusicBrainz** — exact match by the track's **ISRC** (a globally unique recording id). No token
   needed, paced to ~1 req/s.
2. **Discogs** — searches by artist + title and uses the release's granular **styles** (e.g. *Deep
   House*, *Roots Reggae*). Requires a free `DISCOGS_TOKEN` (via `configure` or the credentials file);
   **skipped if unset**.
3. **Spotify** — the artist's genres (batched, always available, no extra setup).

Lookups are cached to a git-ignored **`.genre-cache.json`**, so re-runs are near-instant and only new
tracks hit the APIs (delete the file to force a refresh).

> **Speed vs. granularity:** MusicBrainz/Discogs are rate-limited (~1/s and 60/min), so the *first* run
> on a large library is slow. Put `spotify` first in `genre_providers` if you prefer speed.

## Extending it

Dimensions are pluggable. A new one (mood, tempo, language, …) is just a small `Classifier` subclass in
`src/spotify_sorter/classify.py` implementing `bucket(track) -> str | None`, added to
`build_classifiers`. Genre and decade ship in the box.

## Development

```bash
pip install -e ".[dev]"
pytest          # classification tests run without Spotify credentials
```

## Project layout

```
src/spotify_sorter/
  auth.py          OAuth (spotipy) — reads SPOTIPY_* env vars
  config.py        load + layer config (bundled default → home → env → --config)
  credentials.py   per-user secrets file (0600), loaded into the environment
  configure.py     the `configure` setup wizard
  library.py       fetch Liked Songs + artist genres + release years + ISRCs
  providers.py     genre-source chain (resolve_genres) + Spotify provider
  musicbrainz.py   MusicBrainz ISRC genre provider
  discogs.py       Discogs genre provider (SDK)
  cache.py         persistent genre-lookup cache
  classify.py      GenreClassifier, DecadeClassifier (pluggable)
  dedupe.py        find + remove duplicate Liked Songs
  sorter.py        plan target playlists, then create/populate idempotently
  cli.py           `spotify-sorter` command
  data/genres.yaml bundled default rules + options (customize via `configure`)
```

## License

MIT — see [LICENSE](LICENSE).
