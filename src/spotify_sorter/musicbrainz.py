"""ISRC-first genre lookup via MusicBrainz (hand-rolled `requests` client).

MusicBrainz exposes a direct ISRC -> recording endpoint that Discogs' search does
not, and needs only a User-Agent (no token). Paced to 1 req/sec per its policy.
"""
from __future__ import annotations

import time

import requests

from .library import Track

_BASE = "https://musicbrainz.org/ws/2"


class MusicBrainzClient:
    def __init__(self, user_agent: str, min_interval: float = 1.0, session=None):
        self.user_agent = user_agent
        self.min_interval = min_interval
        self._last = 0.0
        self.session = session or requests.Session()

    def _throttle(self) -> None:
        if self.min_interval <= 0:
            return
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def _request(self, path: str, **params):
        """One paced GET, retried once if MusicBrainz reports it is busy.

        The pacing belongs here, per request, not per track: a lookup costs two requests
        and both count against the 1 req/sec policy.
        """
        def go():
            self._throttle()
            return self.session.get(
                f"{_BASE}/{path}",
                params={**params, "fmt": "json"},
                headers={"User-Agent": self.user_agent},
                timeout=15,
            )

        resp = go()
        if resp.status_code == 503:  # "busy"/rate-limited -> wait and retry once
            time.sleep(max(self.min_interval, 1.0))
            resp = go()
        return resp

    def _recording_id_for_isrc(self, isrc: str) -> str | None:
        """The id of the recording an ISRC identifies, or None if there is no usable one.

        An ISRC may identify several recordings; the first is used, so the work per track
        stays proportional to a single recording however many it resolves to.
        """
        resp = self._request(f"isrc/{isrc}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        for rec in resp.json().get("recordings", []):
            if rec.get("id"):
                return rec["id"]
        return None

    def genres_for_isrc(self, isrc: str) -> list[str]:
        """Genres of the recording an ISRC identifies.

        Two lookups, because genres belong to the recording and the ISRC resource does not
        carry them — asking it for them is rejected outright ("genres is not a valid inc
        parameter for the isrc resource"). Callers cache the result including an empty one,
        so the second lookup is paid once per ISRC rather than once per run.
        """
        mbid = self._recording_id_for_isrc(isrc)
        if mbid is None:
            return []
        resp = self._request(f"recording/{mbid}", inc="genres")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        genres: list[str] = []
        for g in resp.json().get("genres", []):
            name = (g.get("name") or "").lower()
            if name and name not in genres:
                genres.append(name)
        return genres


class MusicBrainzGenreProvider:
    name = "musicbrainz"

    def __init__(self, user_agent: str, cache, client: MusicBrainzClient | None = None,
                 min_interval: float = 1.0):
        self.cache = cache
        self.client = client or MusicBrainzClient(user_agent, min_interval=min_interval)

    def genres_for(self, tracks: list[Track]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for t in tracks:
            if not t.isrc:
                continue  # ISRC-only source; tracks without one fall through
            key = f"mb:{t.isrc}"
            cached = self.cache.get(key)
            if cached is None:
                cached = self.client.genres_for_isrc(t.isrc)
                self.cache.set(key, cached)
            if cached:
                out[t.id] = cached
        return out
