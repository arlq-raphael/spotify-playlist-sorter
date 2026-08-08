"""Load and represent the genre/decade configuration.

The bundled default ships inside the package at ``spotify_sorter/data/genres.yaml``
and holds every default value. Configuration is then assembled by deep-merging up to
four layers (lowest to highest precedence): the bundled default, a per-user config at
``~/.config/spotify-sorter/config.yaml`` (honoring ``$XDG_CONFIG_HOME``), a file named
by ``$SPOTIFY_SORTER_CONFIG``, and a file passed with ``--config``. Each layer may be
partial and overrides only the keys it sets, inheriting the rest.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

import yaml

# The bundled default ships as a package resource, so it is available for every install
# method (wheel, pipx, editable, clone) without depending on the working directory.
_DEFAULT_RESOURCE = files("spotify_sorter") / "data" / "genres.yaml"

# Environment variable naming an extra config file (layered above the home config).
_ENV_CONFIG_VAR = "SPOTIFY_SORTER_CONFIG"


def _user_config_path() -> Path:
    """The per-user config location: ``$XDG_CONFIG_HOME``/``~/.config`` + spotify-sorter/."""
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "spotify-sorter" / "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` onto ``base`` (dicts merge, other values replace)."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class Bucket:
    name: str
    match: list[str]


@dataclass
class Config:
    genre_buckets: list[Bucket]
    decades_enabled: bool = True
    decade_format: str = "{decade}s"
    decade_floor: int | None = 1950
    unmatched_genre_bucket: str | None = "Other"
    no_genre_bucket: str | None = "Unknown Genre"
    playlist_prefix: str = ""
    public_playlists: bool = True
    genre_providers: list[str] = field(default_factory=lambda: ["spotify"])
    discogs_user_agent: str = ""
    musicbrainz_user_agent: str = ""
    cache_path: str = ".genre-cache.json"
    raw: dict = field(default_factory=dict)

    @classmethod
    def defaults(cls) -> Config:
        """Config built from only the bundled default (no user layers) — the canonical
        defaults, used e.g. by the ``configure`` wizard to show/compare defaults."""
        return cls._from_dict(yaml.safe_load(_DEFAULT_RESOURCE.read_text(encoding="utf-8")) or {})

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> Config:
        # Layer 1: the packaged default is always present and is the merge base.
        data = yaml.safe_load(_DEFAULT_RESOURCE.read_text(encoding="utf-8")) or {}

        # Layer 2: the per-user config is auto-discovered; its absence is not an error.
        home = _user_config_path()
        if home.is_file():
            data = _deep_merge(data, yaml.safe_load(home.read_text(encoding="utf-8")) or {})

        # Layers 3-4: explicitly named files (env var, then --config). Named-but-missing
        # is a user error and raises — you asked for that file and it is not there.
        for named in (os.environ.get(_ENV_CONFIG_VAR), path):
            if named is None:
                continue
            p = Path(named)
            if not p.exists():
                raise FileNotFoundError(
                    f"Config file not found: {p}. Pass an existing path with --config, "
                    f"or unset {_ENV_CONFIG_VAR}."
                )
            data = _deep_merge(data, yaml.safe_load(p.read_text(encoding="utf-8")) or {})

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> Config:
        opts = data.get("options", {}) or {}
        dec = data.get("decades", {}) or {}
        discogs = data.get("discogs", {}) or {}
        mb = data.get("musicbrainz", {}) or {}
        cache = data.get("cache", {}) or {}
        buckets = [
            Bucket(name=b["name"], match=[m.lower() for m in b.get("match", [])])
            for b in data.get("genre_buckets", [])
        ]
        # Values come from the (merged) config; sentinels below only guard a corrupt file.
        return cls(
            genre_buckets=buckets,
            decades_enabled=bool(dec.get("enabled", True)),
            decade_format=dec.get("format", "{decade}s"),
            decade_floor=dec.get("floor", 1950),
            unmatched_genre_bucket=opts.get("unmatched_genre_bucket", "Other"),
            no_genre_bucket=opts.get("no_genre_bucket", "Unknown Genre"),
            playlist_prefix=opts.get("playlist_prefix", "") or "",
            public_playlists=bool(opts.get("public_playlists", True)),
            genre_providers=[p.lower() for p in (data.get("genre_providers") or ["spotify"])],
            discogs_user_agent=discogs.get("user_agent", ""),
            musicbrainz_user_agent=mb.get("user_agent", ""),
            cache_path=cache.get("path", ".genre-cache.json"),
            raw=data,
        )
