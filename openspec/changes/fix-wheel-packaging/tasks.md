# Tasks — fix-wheel-packaging

## 1. Relocate the bundled config into the package
- [ ] 1.1 Create `src/spotify_sorter/data/` and move `config/genres.yaml` to `src/spotify_sorter/data/genres.yaml` (single canonical copy)
- [ ] 1.2 Remove the now-empty top-level `config/` directory

## 2. Load the default via importlib.resources
- [ ] 2.1 In `config.py`, replace `_DEFAULT_CONFIG` and `_bundled_default_path()` with an `importlib.resources.files("spotify_sorter") / "data" / "genres.yaml"` resource
- [ ] 2.2 Simplify `Config.load()` to always use the packaged resource as the merge base; keep `--config` filesystem read + deep-merge; keep the missing-user-path `FileNotFoundError`
- [ ] 2.3 Update the module docstring to describe the packaged-resource location

## 3. User config discovery and precedence chain
- [ ] 3.1 Add `_user_config_path()` resolving `$XDG_CONFIG_HOME` or `~/.config`, then `spotify-sorter/config.yaml`
- [ ] 3.2 Rework `Config.load()` to merge layers low→high: bundled default → home config (skip if absent) → `$SPOTIFY_SORTER_CONFIG` (raise if set-but-missing) → `--config` (raise if given-but-missing)
- [ ] 3.3 Keep the missing-explicit-path `FileNotFoundError` message clear and naming the path

## 4. Configure command (config-setup)
- [ ] 4.1 Add `configure.py`: collect settings (injectable `prompt`/`secret_prompt`/`out`), compare against bundled defaults, emit only changed values as nested YAML
- [ ] 4.2 Write the partial config to the resolved home path; overwrite guard (refuse unless `--force`, exit non-zero, touch nothing first)
- [ ] 4.3 Line-aware `.env` write for `DISCOGS_TOKEN` (update in place or append; never rewrite unrelated lines); mask entry via `getpass`; keep the token out of the YAML
- [ ] 4.4 Wire `configure` subcommand into `cli.py` with flags (`--prefix`, `--public/--private`, `--providers`, `--decade-floor`, `--discogs-token`, `--force`, `--non-interactive`) and print the written path

## 5. Packaging metadata
- [ ] 5.1 Update `pyproject.toml` `[tool.setuptools.package-data]` to `spotify_sorter = ["data/*.yaml"]`

## 6. Tests
- [ ] 6.1 Replace `test_load_falls_back_to_cwd` and `test_no_config_anywhere_raises` with `test_load_uses_packaged_default` and `test_packaged_default_resource_exists`
- [ ] 6.2 Keep and re-verify `test_load_explicit_path`, `test_load_missing_path_raises`, `test_user_config_deep_merges_over_bundled_defaults`
- [ ] 6.3 Add precedence tests (home/XDG/env/flag, and the named-missing vs auto-absent asymmetry), monkeypatching home/XDG/env into `tmp_path` so the real home is never touched
- [ ] 6.4 Add an install-shape guard: assert the built wheel contains `spotify_sorter/data/genres.yaml` (or, if `build` is unavailable, assert the resource resolves and no top-level `config/` dir remains)
- [ ] 6.5 `test_configure.py`: wizard writes only changed settings (partial config); empty answers keep defaults; round-trip load yields user value + inherited defaults
- [ ] 6.6 `test_configure.py`: Discogs token goes to `.env` (update-in-place and append cases) and never into the YAML; overwrite guard refuses without `--force` and honors `--force`; non-interactive flag mode writes without stdin

## 7. Docs
- [ ] 7.1 Update `README.md` references from `config/genres.yaml` to the packaged location
- [ ] 7.2 Document the `configure` command, the user config file location (`~/.config/spotify-sorter/config.yaml`, `$XDG_CONFIG_HOME`), the `$SPOTIFY_SORTER_CONFIG` env var, and the precedence order

## 8. Verify
- [ ] 8.1 Run `ruff check` and `pytest` — all green, coverage floor still met
- [ ] 8.2 `openspec validate fix-wheel-packaging --strict` passes
