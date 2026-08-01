"""Load and represent the genre/decade configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Default config ships in the repo's top-level config/ dir.
_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config" / "genres.yaml"


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
    raw: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> Config:
        if path:
            p = Path(path)
        else:
            # Prefer the repo's config/; fall back to ./config/ when run from a clone.
            p = _DEFAULT_CONFIG
            if not p.exists():
                p = Path.cwd() / "config" / "genres.yaml"
        if not p.exists():
            raise FileNotFoundError(
                f"Config file not found: {p}. Pass one with --config, or copy config/genres.yaml."
            )
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        opts = data.get("options", {}) or {}
        dec = data.get("decades", {}) or {}
        buckets = [
            Bucket(name=b["name"], match=[m.lower() for m in b.get("match", [])])
            for b in data.get("genre_buckets", [])
        ]
        return cls(
            genre_buckets=buckets,
            decades_enabled=bool(dec.get("enabled", True)),
            decade_format=dec.get("format", "{decade}s"),
            decade_floor=dec.get("floor", 1950),
            unmatched_genre_bucket=opts.get("unmatched_genre_bucket", "Other"),
            no_genre_bucket=opts.get("no_genre_bucket", "Unknown Genre"),
            playlist_prefix=opts.get("playlist_prefix", "") or "",
            public_playlists=bool(opts.get("public_playlists", True)),
            raw=data,
        )
