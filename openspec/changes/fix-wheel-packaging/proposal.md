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
- **BREAKING** (internal only): remove the `_DEFAULT_CONFIG` path constant and the
  `cwd/config/genres.yaml` fallback. No public CLI behaviour regresses for
  correctly-installed users; the change *fixes* wheel installs and *adds* the user-config
  layer.

## Capabilities

### New Capabilities
- `config-loading` — how the tool locates, layers, and loads its default and user
  configuration: the packaged default plus the home-directory / env / flag precedence
  chain, independent of installation method.

### Modified Capabilities
- None. (`dedupe` and `genre-providers` requirements are unchanged; they benefit from
  `Config.load()` no longer failing and from honoring a user config.)

## Impact

- `src/spotify_sorter/config.py` — resource-based default loading + precedence chain.
- `config/genres.yaml` → `src/spotify_sorter/data/genres.yaml` (moved).
- `pyproject.toml` — in-package `package-data` entry.
- `tests/test_config.py` — replace cwd-fallback tests; add packaged-resource, home-config
  discovery, env-var, and precedence/merge-order tests.
- `README.md` — document the user config location and precedence.
- No new runtime dependency (`importlib.resources` and XDG-path resolution are stdlib on
  Python 3.9+).
