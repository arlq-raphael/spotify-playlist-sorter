# Config loading: ship the bundled default in the wheel and support a user config file

## Why

Two gaps in how the tool loads configuration:

1. **The bundled default doesn't ship in a wheel.** `config/genres.yaml` lives
   *outside* the Python package and is declared as `package-data = ["../config/*.yaml"]`.
   setuptools ignores `../` escapes, so the wheel contains no config. At runtime
   `Config.load()` resolves the default via `Path(__file__).parent.parent.parent/config`
   (only correct in an editable checkout) and otherwise falls back to
   `./config/genres.yaml` in the current working directory. A wheel/`pipx` install run
   from any non-clone directory therefore fails with `FileNotFoundError` on both `sort`
   and `dedupe`. Only `pip install -e` works today.

2. **There is no persistent user config.** Customizing buckets, provider order, or the
   playlist prefix requires passing `--config <path>` on every invocation. A CLI like
   this should read a user-level config from a standard home-directory location (as the
   AWS CLI reads `~/.aws/config`), so a user configures once and runs bare thereafter.

## What Changes

- **Package the default config.** Move `config/genres.yaml` into the package at
  `src/spotify_sorter/data/genres.yaml` and load it via `importlib.resources`, so it is
  available for every install method (wheel, pipx, editable, clone) without depending on
  the current working directory.
- **Add a user config file** at `~/.config/spotify-sorter/config.yaml` (honoring
  `$XDG_CONFIG_HOME`), discovered automatically when present.
- **Define a deterministic precedence chain**, each layer deep-merged over the previous
  (highest wins), so every layer may be partial and inherit the rest:
  1. bundled default (always the base)
  2. user config at `~/.config/spotify-sorter/config.yaml`
  3. `$SPOTIFY_SORTER_CONFIG` env var path
  4. `--config <path>` explicit flag
- Keep `--config` working; it becomes the top layer of the chain rather than the only
  user layer.
- **Add a per-user credentials file** at `~/.config/spotify-sorter/credentials`
  (honoring `$XDG_CONFIG_HOME`), separate from the preferences YAML, holding secrets
  (`DISCOGS_TOKEN`, and optionally the Spotify app `SPOTIPY_CLIENT_ID/SECRET/REDIRECT_URI`)
  as `KEY=VALUE` lines. It is written with owner-only permissions (`0600`) and loaded at
  startup with precedence: real env var → project `./.env` → home credentials file. This
  mirrors the aws-cli split of `~/.aws/config` (preferences) vs `~/.aws/credentials`
  (secrets), and gives a globally-installed CLI a persistent per-user secret store instead
  of a working-directory-bound `.env`.
- **Add a `configure` command** — an interactive wizard (aws-configure-style) that
  prompts for the common settings and writes a minimal user config to the home location,
  so users never hand-write YAML. It writes only the settings the user changed (a partial
  config that keeps inheriting the rest), refuses to overwrite an existing file without
  `--force`, and keeps secrets out of the YAML: the Discogs token (and, optionally, the
  Spotify app credentials) are written to the `0600` credentials file, never into the
  config. Every prompt also has a flag, and a `--non-interactive` mode makes it scriptable
  and testable.
- **BREAKING** (internal only): remove the `_DEFAULT_CONFIG` path constant and the
  `cwd/config/genres.yaml` fallback. No public CLI behaviour regresses for
  correctly-installed users; the change *fixes* wheel installs and *adds* the user-config
  layer.

## Capabilities

### New Capabilities
- `config-loading` — how the tool locates, layers, and loads its default and user
  configuration: the packaged default plus the home-directory / env / flag precedence
  chain, independent of installation method.
- `credentials` — how the tool locates and loads secrets (Discogs token, Spotify app
  credentials) from a per-user credentials file and the environment, separate from the
  preferences config, with owner-only file permissions.
- `config-setup` — the `configure` command that interactively generates a user config
  at the home location and writes secrets to the credentials file.

### Modified Capabilities
- None. (`dedupe` and `genre-providers` requirements are unchanged; they benefit from
  `Config.load()` no longer failing and from honoring a user config.)

## Impact

- `src/spotify_sorter/config.py` — resource-based default loading + precedence chain.
- `config/genres.yaml` → `src/spotify_sorter/data/genres.yaml` (moved).
- `src/spotify_sorter/credentials.py` (new) — resolve the credentials-file path, load
  secrets into the environment (`setdefault`) at startup, and a `0600` line-aware writer.
- `src/spotify_sorter/cli.py` — load the credentials file alongside `.env` at startup.
- `src/spotify_sorter/configure.py` (new) — the wizard logic (prompt/collect/write),
  wired into `cli.py` as the `configure` subcommand.
- `pyproject.toml` — in-package `package-data` entry.
- `tests/test_config.py` — replace cwd-fallback tests; add packaged-resource, home-config
  discovery, env-var, and precedence/merge-order tests.
- `tests/test_credentials.py` (new) — path resolution, load precedence (env / `.env` /
  home), `0600` permissions, line-aware update/append.
- `tests/test_configure.py` (new) — wizard prompt handling, partial-config output,
  credentials-file token write, overwrite guard.
- `README.md` — document the `configure` command, the user config location, and precedence.
- No new runtime dependency (`importlib.resources`, XDG-path resolution, and `getpass`
  for masked token entry are all stdlib on Python 3.9+).
