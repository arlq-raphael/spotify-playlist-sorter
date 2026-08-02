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

## 4. Packaging metadata
- [ ] 4.1 Update `pyproject.toml` `[tool.setuptools.package-data]` to `spotify_sorter = ["data/*.yaml"]`

## 5. Tests
- [ ] 5.1 Replace `test_load_falls_back_to_cwd` and `test_no_config_anywhere_raises` with `test_load_uses_packaged_default` and `test_packaged_default_resource_exists`
- [ ] 5.2 Keep and re-verify `test_load_explicit_path`, `test_load_missing_path_raises`, `test_user_config_deep_merges_over_bundled_defaults`
- [ ] 5.3 Add precedence tests (home/XDG/env/flag, and the named-missing vs auto-absent asymmetry), monkeypatching home/XDG/env into `tmp_path` so the real home is never touched
- [ ] 5.4 Add an install-shape guard: assert the built wheel contains `spotify_sorter/data/genres.yaml` (or, if `build` is unavailable, assert the resource resolves and no top-level `config/` dir remains)

## 6. Docs
- [ ] 6.1 Update `README.md` references from `config/genres.yaml` to the packaged location
- [ ] 6.2 Document the user config file location (`~/.config/spotify-sorter/config.yaml`, `$XDG_CONFIG_HOME`), the `$SPOTIFY_SORTER_CONFIG` env var, and the precedence order

## 7. Verify
- [ ] 7.1 Run `ruff check` and `pytest` — all green, coverage floor still met
- [ ] 7.2 `openspec validate fix-wheel-packaging --strict` passes
