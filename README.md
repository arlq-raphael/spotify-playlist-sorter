# spotify-playlist-sorter

[![CI](https://github.com/arlq-raphael/spotify-playlist-sorter/actions/workflows/ci.yml/badge.svg)](https://github.com/arlq-raphael/spotify-playlist-sorter/actions/workflows/ci.yml)

Sort your Spotify **Liked Songs** into tidy per-**genre** and per-**decade** playlists — automatically,
and idempotently (re-run any time to file only what's new).

Classification is deterministic and offline-friendly: it reads the **genres Spotify already assigns to
each artist** and the **album release year**, then maps them to bucket playlists via an editable rules
file. No LLM, no extra API keys — just your Spotify app credentials.

```
Liked Songs ──► [ genre buckets ]   Reggae Roots & Dub, Hip-Hop / Rap, House / Electro, Jazz, …
            └─► [ decade buckets ]  1960s, 1970s, 1980s, 1990s, 2000s, 2010s, 2020s
```

## Install

```bash
git clone https://github.com/arlq/spotify-playlist-sorter
cd spotify-playlist-sorter
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Set up Spotify credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → **Create app**.
2. In the app's settings, add this exact **Redirect URI**: `http://127.0.0.1:8888/callback`
3. Copy your **Client ID** and **Client Secret**, then:

```bash
cp .env.example .env
# edit .env and fill in SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET
```

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

## How genre classification works

For each track, the tool collects the Spotify genres of its artists and walks the `genre_buckets` list
in `config/genres.yaml` **top to bottom**, choosing the **first** bucket whose any `match` substring
appears in any of those genres. **Order = priority**, so more specific buckets go above generic ones
(e.g. `Ragga / Dancehall` before `Reggae Roots & Dub`, so a *dancehall* track lands in Ragga).

Edit `config/genres.yaml` to rename buckets, reorder priorities, or add your own — for example:

```yaml
genre_buckets:
  - name: "French Rap"
    match: [french hip hop, rap francais]
  - name: "Hip-Hop / Rap"
    match: [hip hop, rap, trap, drill]
```

Options in the same file control fallbacks (`unmatched_genre_bucket`, `no_genre_bucket`), a playlist
name `prefix`, public/private playlists, and the decade `floor`.

> **Note:** Spotify returns genres per *artist*, not per track, and smaller artists often have none —
> those land in the `no_genre_bucket` ("Unknown Genre") so nothing is silently dropped.

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
  auth.py       OAuth (spotipy) — reads SPOTIPY_* env vars
  library.py    fetch Liked Songs + artist genres + release years
  classify.py   GenreClassifier, DecadeClassifier (pluggable)
  sorter.py     plan target playlists, then create/populate idempotently
  cli.py        `spotify-sorter` command
config/genres.yaml   editable genre→bucket rules + options
```

## License

MIT — see [LICENSE](LICENSE).
