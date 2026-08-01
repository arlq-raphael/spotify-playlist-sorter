"""Classifiers turn a Track into a target playlist name for one dimension.

Adding a new dimension (mood, tempo, …) is just a new Classifier subclass that
implements `bucket(track) -> str | None`.
"""
from __future__ import annotations

from typing import Protocol

from .config import Config
from .library import Track


class Classifier(Protocol):
    dimension: str

    def bucket(self, track: Track) -> str | None:
        """Return the playlist name for this track, or None to skip it."""
        ...


class GenreClassifier:
    dimension = "genre"

    def __init__(self, config: Config):
        self.buckets = config.genre_buckets
        self.unmatched = config.unmatched_genre_bucket
        self.no_genre = config.no_genre_bucket

    def bucket(self, track: Track) -> str | None:
        if not track.genres:
            return self.no_genre
        for b in self.buckets:  # ordered: first match wins
            for needle in b.match:
                if any(needle in g for g in track.genres):
                    return b.name
        return self.unmatched


class DecadeClassifier:
    dimension = "decade"

    def __init__(self, config: Config):
        self.fmt = config.decade_format
        self.floor = config.decade_floor

    def bucket(self, track: Track) -> str | None:
        year = track.release_year
        if year is None:
            return None
        if self.floor is not None and year < self.floor:
            year = self.floor
        decade = (year // 10) * 10
        return self.fmt.format(decade=decade)


def build_classifiers(config: Config, dimensions: list[str]) -> list[Classifier]:
    available: dict[str, Classifier] = {"genre": GenreClassifier(config)}
    if config.decades_enabled:
        available["decade"] = DecadeClassifier(config)
    out: list[Classifier] = []
    for d in dimensions:
        if d not in available:
            raise SystemExit(f"Unknown or disabled dimension: {d!r} (available: {sorted(available)})")
        out.append(available[d])
    return out
