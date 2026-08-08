# Tasks — fix-wheel-packaging

## 1. Relocate the bundled config into the package
- [x] 1.1 Create `src/spotify_sorter/data/` and move `config/genres.yaml` to `src/spotify_sorter/data/genres.yaml` (single canonical copy)
- [x] 1.2 Remove the now-empty top-level `config/` directory

## 2. Load the default via importlib.resources
- [x] 2.1 In `config.py`, replace `_DEFAULT_CONFIG` and `_bundled_default_path()` with an `importlib.resources.files("spotify_sorter") / "data" / "genres.yaml"` resource
- [x] 2.2 Simplify `Config.load()` to always use the packaged resource as the merge base; keep `--config` filesystem read + deep-merge; keep the missing-user-path `FileNotFoundError`
- [x] 2.3 Update the module docstring to describe the packaged-resource location

## 3. User config discovery and precedence chain
- [x] 3.1 Add `_user_config_path()` resolving `$XDG_CONFIG_HOME` or `~/.config`, then `spotify-sorter/config.yaml`
- [x] 3.2 Rework `Config.load()` to merge layers low→high: bundled default → home config (skip if absent) → `$SPOTIFY_SORTER_CONFIG` (raise if set-but-missing) → `--config` (raise if given-but-missing)
- [x] 3.3 Keep the missing-explicit-path `FileNotFoundError` message clear and naming the path

## 4. Credentials file (credentials)
- [x] 4.1 Add `credentials.py`: `_credentials_path()` (`$XDG_CONFIG_HOME`/`~/.config` → `spotify-sorter/credentials`)
- [x] 4.2 `load_credentials_into_env()` — parse `KEY=VALUE` and `os.environ.setdefault` each key; call it at CLI startup *after* `_load_dotenv()` (precedence: env → `./.env` → home credentials)
- [x] 4.3 `write_credential(key, value)` — line-aware upsert, create parent dir, write `0600` from the start (secret never briefly world-readable)
- [x] 4.4 Recognize `DISCOGS_TOKEN`, `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI`; no provider/auth call-site changes needed (they read env)

## 5. Configure command (config-setup)
- [x] 5.1 Add `configure.py`: collect settings (injectable `prompt`/`secret_prompt`/`out`), compare against bundled defaults, emit only changed values as nested YAML
- [x] 5.2 Write the partial config to the resolved home path; overwrite guard (refuse unless `--force`, exit non-zero, touch nothing first)
- [x] 5.3 Collect secrets (Discogs token; optional Spotify app credentials) via masked `getpass` and persist them through `credentials.write_credential` — never into the YAML
- [x] 5.4 Wire `configure` subcommand into `cli.py` with flags (`--prefix`, `--public/--private`, `--providers`, `--decade-floor`, `--discogs-token`, `--spotify-client-id/-secret/-redirect`, `--force`, `--non-interactive`) and print the written paths

## 6. Packaging metadata
- [x] 6.1 Update `pyproject.toml` `[tool.setuptools.package-data]` to `spotify_sorter = ["data/*.yaml"]`

## 7. Tests
- [x] 7.1 Replace `test_load_falls_back_to_cwd` and `test_no_config_anywhere_raises` with `test_load_uses_packaged_default` and `test_packaged_default_resource_exists`
- [x] 7.2 Keep and re-verify `test_load_explicit_path`, `test_load_missing_path_raises`, `test_user_config_deep_merges_over_bundled_defaults`
- [x] 7.3 Add precedence tests (home/XDG/env/flag, and the named-missing vs auto-absent asymmetry), monkeypatching home/XDG/env into `tmp_path` so the real home is never touched
- [x] 7.4 Add an install-shape guard: assert the built wheel contains `spotify_sorter/data/genres.yaml` (or, if `build` is unavailable, assert the resource resolves and no top-level `config/` dir remains)
- [x] 7.5 `test_credentials.py`: path resolution; load precedence (env > `.env` > home); missing file is silent; `write_credential` sets `0600` and updates in place / appends
- [x] 7.6 `test_configure.py`: wizard writes only changed settings (partial config); empty answers keep defaults; round-trip load yields user value + inherited defaults
- [x] 7.7 `test_configure.py`: Discogs/Spotify secrets go to the credentials file (`0600`, never the YAML); overwrite guard refuses without `--force` and honors `--force`; non-interactive flag mode writes without stdin (redirect home/creds paths into `tmp_path`)

## 8. Docs
- [x] 8.1 Update `README.md` references from `config/genres.yaml` to the packaged location
- [x] 8.2 Document the `configure` command, the user config file (`~/.config/spotify-sorter/config.yaml`, `$XDG_CONFIG_HOME`, `$SPOTIFY_SORTER_CONFIG`, precedence), and the credentials file (`~/.config/spotify-sorter/credentials`, `0600`, secret precedence env → `.env` → credentials)

## 9. Verify
- [x] 9.1 Run `ruff check` and `pytest` — all green, coverage floor still met
- [x] 9.2 `openspec validate fix-wheel-packaging --strict` passes
