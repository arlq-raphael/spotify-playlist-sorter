"""Discogs genre provider via the python3-discogs-client SDK.

Searches by artist + track title and reads the best result's genre + style. The
SDK handles token auth, User-Agent, and rate limiting. Token-gated: no
DISCOGS_TOKEN means the provider is skipped.
"""
from __future__ import annotations

import os

import discogs_client

from .config import Config
from .library import Track


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def build_discogs_provider(config: Config, cache, notify=print):
    token = os.environ.get("DISCOGS_TOKEN")
    if not token:
        notify("discogs: no DISCOGS_TOKEN set — skipping (falling back to the next genre source).")
        return None
    client = discogs_client.Client(config.discogs_user_agent, user_token=token)
    return DiscogsGenreProvider(client, cache)


class DiscogsGenreProvider:
    name = "discogs"

    def __init__(self, client, cache):
        self.client = client
        self.cache = cache

    def genres_for(self, tracks: list[Track]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for t in tracks:
            key = f"dg:{_norm(t.primary_artist)}|{_norm(t.name)}"
            cached = self.cache.get(key)
            if cached is None:
                cached = self._search(t)
                self.cache.set(key, cached)
            if cached:
                out[t.id] = cached
        return out

    def _search(self, t: Track) -> list[str]:
        results = self.client.search(type="release", artist=t.primary_artist, track=t.name)
        try:
            first = results[0]
        except IndexError:
            return []
        data = getattr(first, "data", {}) or {}
        raw = list(data.get("genre") or data.get("genres") or [])
        raw += list(data.get("style") or data.get("styles") or [])
        genres: list[str] = []
        for g in raw:
            g = str(g).lower()
            if g not in genres:
                genres.append(g)
        return genres
