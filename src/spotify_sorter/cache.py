"""Persistent JSON cache of external genre lookups, keyed by lookup key.

Stores resolved genre lists — including empty lists for known misses — so neither
a hit nor a miss is re-queried on a later run.
"""
from __future__ import annotations

import json
from pathlib import Path


class GenreCache:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data: dict[str, list[str]] = {}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data = loaded
            except (ValueError, OSError):
                self.data = {}
        self._dirty = False

    def get(self, key: str) -> list[str] | None:
        """Return the cached genres (possibly empty), or None if not cached."""
        return self.data.get(key)

    def set(self, key: str, genres: list[str]) -> None:
        self.data[key] = list(genres)
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
            self._dirty = False
        except OSError:
            pass
