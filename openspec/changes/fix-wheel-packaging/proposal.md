# Fix wheel packaging so the bundled config ships with the installed package

## Why

The bundled default config lives at the repo-root `config/genres.yaml`, *outside*
the Python package, and is declared as `package-data = ["../config/*.yaml"]`.
setuptools cannot include a file above the package via `../`, so the wheel ships
no config. At runtime `Config.load()` resolves the default via
`Path(__file__).parent.parent.parent / "config"` (only correct in an editable
checkout) and otherwise falls back to `./config/genres.yaml` in the current
working directory. Consequently a user who installs from a wheel (`pip install`,
`pipx`) and runs `spotify-sorter sort` or `spotify-sorter dedupe` from any
directory other than a repo clone gets a `FileNotFoundError`. The tool is
effectively broken for its primary distribution path; only `pip install -e`
(editable) works today.

## What Changes

- Move `config/genres.yaml` into the package at `src/spotify_sorter/data/genres.yaml`
  so it is a genuine package resource that ships in the wheel.
- Load the bundled default via `importlib.resources` (package-relative), removing
  the `parent.parent.parent` path walk and the `./config/` current-working-directory
  fallback.
- Update `pyproject.toml` `package-data` to reference the in-package resource
  (no `../` escape).
- Keep `--config <path>` behaviour unchanged: an explicit user config is still
  read from the filesystem and deep-merged over the bundled default.
- Update tests that encode the old on-disk/cwd fallback assumptions to assert the
  new packaged-resource behaviour.
- **BREAKING** (internal only): the module-level `_DEFAULT_CONFIG` path constant
  and the `cwd/config/genres.yaml` fallback are removed. No public CLI behaviour
  changes for correctly-installed users; the change *fixes* behaviour for wheel
  installs.

## Capabilities

### New Capabilities
- `config-loading` — how the tool locates and loads its default and user configuration,
  independent of installation method (wheel, pipx, editable, or source clone).

### Modified Capabilities
- None. (`dedupe` and `genre-providers` requirements are unchanged; they merely
  benefit from `Config.load()` no longer failing.)

## Impact

- `src/spotify_sorter/config.py` — resource-based default loading.
- `config/genres.yaml` → `src/spotify_sorter/data/genres.yaml` (moved).
- `pyproject.toml` — `package-data` entry.
- `tests/test_config.py` — replace cwd-fallback tests with packaged-resource tests.
- No new runtime dependency (`importlib.resources` is stdlib; the `.files()` API is
  available on Python 3.9+).
- References to `config/genres.yaml` in `README.md` and `config/genres.yaml`-relative
  docs updated to the new location.
