# Design — fix-wheel-packaging

## Context

`Config.load()` currently finds the bundled default like this:

```python
_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "genres.yaml"
# ...
return _DEFAULT_CONFIG if _DEFAULT_CONFIG.exists() else Path.cwd() / "config" / "genres.yaml"
```

`__file__` is `.../spotify_sorter/config.py`, so `parent.parent.parent` is the
directory *above* the package. In an editable install that is the repo root (which
has `config/genres.yaml`), so it works. In a wheel install it is the directory
above `site-packages/spotify_sorter/`, which never contains `config/`, so it falls
back to `./config/genres.yaml` under the process's CWD — present only if the user
happens to run from a clone. `pyproject.toml` tries to bundle the file with
`package-data = ["../config/*.yaml"]`, but setuptools ignores `../` escapes, so the
file is not in the wheel at all (absent from `SOURCES.txt`).

## Goals

- The bundled default config is importable data that ships in the wheel.
- Loading it does not depend on CWD or on the source-tree layout.
- `--config` behaviour (filesystem read + deep-merge over default) is unchanged.
- Works on Python 3.9+ (the project's floor).

## Decision

Move the file **into** the package and load it as a package resource.

1. **Relocate**: `config/genres.yaml` → `src/spotify_sorter/data/genres.yaml`.
   Keep a single canonical copy inside the package; there is no second copy at the
   repo root (avoids drift). The `config/` directory at the repo root is removed.

2. **Load via `importlib.resources`**:
   ```python
   from importlib.resources import files
   _DEFAULT_RESOURCE = files("spotify_sorter") / "data" / "genres.yaml"
   ...
   text = _DEFAULT_RESOURCE.read_text(encoding="utf-8")
   ```
   `importlib.resources.files()` is available in the stdlib from Python 3.9, so no
   `importlib_resources` backport dependency is needed. The returned `Traversable`
   supports `.read_text()` and `.is_file()` directly; no `as_file`/tempfile dance is
   required because we only read text, never need a real filesystem path.

3. **`pyproject.toml`**: replace
   `package-data = { spotify_sorter = ["../config/*.yaml"] }` with
   `package-data = { spotify_sorter = ["data/*.yaml"] }` (an in-package glob that
   setuptools includes). `[tool.setuptools.packages.find]` already discovers
   `spotify_sorter`; the `data/` folder ships because it is package-data, not a
   package, so it does not need an `__init__.py`.

4. **Remove** the module-level `_DEFAULT_CONFIG` filesystem constant, the
   `_bundled_default_path()` cwd fallback, and the "default not found" branch that
   only fired when both the path walk and the cwd guess missed. With a packaged
   resource the default is *always* present; a missing bundled resource now
   indicates a broken install, which we surface as a clear error rather than a
   silent cwd guess.

## Config.load() shape after the change

```python
@classmethod
def load(cls, path: str | os.PathLike | None = None) -> Config:
    base = yaml.safe_load(_DEFAULT_RESOURCE.read_text(encoding="utf-8")) or {}
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}. ...")
        data = _deep_merge(base, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    else:
        data = base
    return cls._from_dict(data)
```

The bundled resource is always the merge base, which also resolves the "defaults in
three places" concern's runtime ambiguity: the YAML is unconditionally present, so
`_from_dict`'s sentinels remain only as corrupt-file guards. (Deduping the sentinels
themselves is out of scope here — tracked separately.)

## Testing strategy

- Replace `test_load_falls_back_to_cwd` and `test_no_config_anywhere_raises` (both
  encode the removed cwd fallback) with:
  - `test_load_uses_packaged_default`: `Config.load()` with no path returns a config
    whose `genre_buckets` is non-empty and `genre_providers` matches the shipped YAML.
  - `test_packaged_default_resource_exists`: assert
    `files("spotify_sorter") / "data" / "genres.yaml"` `.is_file()`.
- Keep `test_load_explicit_path`, `test_load_missing_path_raises`, and
  `test_user_config_deep_merges_over_bundled_defaults` (all still valid).
- **Install-shape guard**: add a test that builds the wheel and asserts
  `data/genres.yaml` is present inside it. Simplest form without a full pip install:
  run `python -m build --wheel` into a temp dir and assert the zip namelist contains
  `spotify_sorter/data/genres.yaml`. If `build` is not a dev dependency, instead
  assert via `importlib.resources` that the resource resolves and the repo no longer
  has a top-level `config/` dir. (Prefer the wheel check; fall back to the resource
  check to avoid adding a heavy dev dep.)

## Alternatives considered

- **Keep the file at repo root, fix `package-data` with `data-files` / MANIFEST.in**:
  `data-files` installs outside the package (into `sys.prefix`), which reintroduces
  path-guessing and is discouraged for wheels. Rejected.
- **Embed the YAML as a Python string literal**: avoids resource loading but makes the
  default config hard to read/diff and duplicates it if we ever want to also ship the
  file for users to copy. Rejected.
- **`importlib_resources` backport dep**: unnecessary on 3.9+. Rejected.

## Risks

- A downstream user or doc that referenced `config/genres.yaml` at the repo root will
  need the new path. Mitigated by updating README and any doc references, and by the
  file still being viewable in the source tree (just under `src/spotify_sorter/data/`).
