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
- A user config at `~/.config/spotify-sorter/config.yaml` is auto-discovered, so users
  configure once instead of passing `--config` every run.
- Layering is deterministic: default → home → env → flag, deep-merged, highest wins.
- `--config` continues to work as the top override layer.
- Works on Python 3.9+ (the project's floor); no new dependency.

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

## User config discovery and precedence

Config is assembled from up to four layers, deep-merged low→high:

| # | Layer | Source | Presence |
|---|-------|--------|----------|
| 1 | bundled default | packaged `data/genres.yaml` resource | always |
| 2 | user config | `~/.config/spotify-sorter/config.yaml` | optional (skipped if absent) |
| 3 | env override | file named by `$SPOTIFY_SORTER_CONFIG` | optional (error if set but missing) |
| 4 | flag override | file named by `--config <path>` | optional (error if given but missing) |

**Home path resolution** (`_user_config_path()`):
```python
base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
return Path(base) / "spotify-sorter" / "config.yaml"
```
`Path.home()` and `$XDG_CONFIG_HOME` are stdlib; no extra dependency. XDG is preferred
over an AWS-style `~/.spotify-sorter/` because it is the modern cross-platform
convention; `~/.aws/` predates XDG.

**Missing-file semantics differ by layer intentionally.** Layer 2 (home) is
*auto-discovered*, so its absence is normal and silently skipped. Layers 3 and 4 are
*explicitly named* by the user, so a missing target is a user error and raises
`FileNotFoundError` — you asked for that file, it isn't there. This mirrors how the AWS
CLI treats an explicit `--profile`/`AWS_CONFIG_FILE` vs. the default location.

**Why layer rather than replace.** `--config` layering on top of the home config
(rather than replacing it) is consistent with the deep-merge model already used for
partial configs: every layer is additive-with-override. A user with a home config who
passes `--config tweak.yaml` for one run gets home ∪ tweak, tweak winning on conflicts —
the least-surprising behavior given partial configs are already the norm here.

## Config.load() shape after the change

```python
@classmethod
def load(cls, path: str | os.PathLike | None = None) -> Config:
    data = yaml.safe_load(_DEFAULT_RESOURCE.read_text(encoding="utf-8")) or {}   # layer 1

    home = cls._user_config_path()                                              # layer 2
    if home.is_file():
        data = _deep_merge(data, yaml.safe_load(home.read_text("utf-8")) or {})

    for layer_path, required in (
        (os.environ.get("SPOTIFY_SORTER_CONFIG"), True),                        # layer 3
        (path, True),                                                           # layer 4
    ):
        if layer_path is None:
            continue
        p = Path(layer_path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}. ...")
        data = _deep_merge(data, yaml.safe_load(p.read_text("utf-8")) or {})

    return cls._from_dict(data)
```

The bundled resource is always the merge base, which also resolves the "defaults in
three places" concern's runtime ambiguity: the YAML is unconditionally present, so
`_from_dict`'s sentinels remain only as corrupt-file guards. (Deduping the sentinels
themselves is out of scope here — tracked separately.)

Note the deliberate asymmetry: layer 2's absence is silent (`is_file()` guard), while
layers 3–4 raise when named-but-missing.

## Configure command (config-setup)

A new `configure` subcommand in `cli.py`, backed by `configure.py`.

**Prompts (each with a flag + default from the bundled config):**

| Setting | Prompt / flag | Written to |
|---------|---------------|------------|
| playlist prefix | `--prefix` | `options.playlist_prefix` |
| public playlists | `--public/--private` | `options.public_playlists` |
| genre providers | `--providers a,b,c` | `genre_providers` |
| earliest decade | `--decade-floor` | `decades.floor` |
| Discogs token | `--discogs-token` | `.env` (`DISCOGS_TOKEN`), **not** the YAML |

**Minimal output.** The wizard compares each answer to the default drawn from the bundled
config; only *changed* values are emitted. So accepting every default writes an
(essentially empty) config — and, more importantly, a config that keeps tracking the
bundled defaults for anything the user didn't deliberately set. YAML is emitted with the
same nesting the loader expects (`options:`, `decades:`, top-level `genre_providers:`).

**Prompting is injectable.** `configure.py` takes `prompt`/`secret_prompt`/`out`
callables (defaulting to `input`, `getpass.getpass`, `print`). `--non-interactive` swaps
in a no-prompt collector that reads only flags + defaults. Tests pass fakes — no real
stdin, no real `getpass`, and the target paths (`config.yaml`, `.env`) are redirected into
`tmp_path`.

**`.env` write is line-aware.** If `.env` exists and has a `DISCOGS_TOKEN=` line, replace
it in place; otherwise append. Never rewrite unrelated lines. The config-path and env-path
are parameters (default: the resolved home config, and `./.env`) so tests and power users
can redirect them.

**Overwrite guard.** If the resolved config path exists and `--force` is not set, print
"already exists — pass --force to overwrite" and return a non-zero exit *before* touching
anything.

**Security note.** The token is masked at entry (`getpass`), never echoed, never logged,
and never placed in the YAML. `.env` is already gitignored. This preserves the existing
config-vs-secrets boundary (preferences in YAML, secrets in env/`.env`).

## Testing strategy

- Replace `test_load_falls_back_to_cwd` and `test_no_config_anywhere_raises` (both
  encode the removed cwd fallback) with:
  - `test_load_uses_packaged_default`: `Config.load()` with no path returns a config
    whose `genre_buckets` is non-empty and `genre_providers` matches the shipped YAML.
  - `test_packaged_default_resource_exists`: assert
    `files("spotify_sorter") / "data" / "genres.yaml"` `.is_file()`.
- Keep `test_load_explicit_path`, `test_load_missing_path_raises`, and
  `test_user_config_deep_merges_over_bundled_defaults` (all still valid).
- Add for the precedence chain (monkeypatch `Path.home`/`$XDG_CONFIG_HOME`/env into
  `tmp_path`, never touching the real home):
  - `test_home_config_discovered`: a partial `~/.config/spotify-sorter/config.yaml`
    overrides its keys and inherits the rest.
  - `test_xdg_config_home_respected`: `$XDG_CONFIG_HOME` redirects the lookup.
  - `test_env_var_config_layer`: `$SPOTIFY_SORTER_CONFIG` is merged over the home layer.
  - `test_flag_overrides_home_and_env`: same key set in all three user layers → flag wins.
  - `test_env_config_missing_raises` / `test_missing_home_config_is_skipped`: the
    named-but-missing vs. auto-discovered-absent asymmetry.
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
