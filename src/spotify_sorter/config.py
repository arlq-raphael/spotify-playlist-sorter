"""Load and represent the genre/decade configuration.

The bundled ``config/genres.yaml`` is the single source of default values. A user
config passed with ``--config`` is deep-merged *over* those defaults, so a partial
config only overrides the keys it sets and inherits the rest from the bundled file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Default config ships in the repo's top-level config/ dir; it holds every default value.
_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "genres.yaml"


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
    def _bundled_default_path(cls) -> Path:
        # The packaged config, or ./config/genres.yaml when run from a clone.
        return _DEFAULT_CONFIG if _DEFAULT_CONFIG.exists() else Path.cwd() / "config" / "genres.yaml"

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> Config:
        default_path = cls._bundled_default_path()
        base = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {} if default_path.exists() else {}

        if path is not None:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(
                    f"Config file not found: {p}. Pass one with --config, or copy config/genres.yaml."
                )
            data = _deep_merge(base, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
        elif base:
            data = base
        else:
            raise FileNotFoundError(
                "Default config not found. Pass one with --config, or copy config/genres.yaml."
            )
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
