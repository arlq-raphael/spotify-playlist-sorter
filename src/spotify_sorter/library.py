"""Read the user's Liked Songs and the genre data needed to classify them."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Callable

import spotipy
from requests.exceptions import RequestException
from spotipy.exceptions import SpotifyException


@dataclass
class Track:
    id: str
    name: str
    artist_ids: list[str]
    artist_names: list[str]
    release_year: int | None
    duration_ms: int | None = None
    isrc: str | None = None
    genres: list[str] = field(default_factory=list)  # filled in later

    @property
    def label(self) -> str:
        return f"{self.name} — {', '.join(self.artist_names)}"

    @property
    def primary_artist(self) -> str:
        return self.artist_names[0] if self.artist_names else ""


def _year_from_release_date(date: str | None) -> int | None:
    if not date:
        return None
    try:
        return int(date[:4])
    except ValueError:
        return None


def fetch_liked_tracks(sp: spotipy.Spotify, limit: int | None = None) -> list[Track]:
    """Page through Liked Songs. `limit` caps the number fetched (None = all)."""
    tracks: list[Track] = []
    offset = 0
    page = 50
    while True:
        res = sp.current_user_saved_tracks(limit=page, offset=offset)
        items = res.get("items", [])
        for it in items:
            t = it.get("track") or {}
            if not t.get("id"):
                continue  # local files / unavailable
            album = t.get("album") or {}
            artists = t.get("artists") or []
            tracks.append(
                Track(
                    id=t["id"],
                    name=t.get("name", ""),
                    artist_ids=[a["id"] for a in artists if a.get("id")],
                    artist_names=[a.get("name", "") for a in artists],
                    release_year=_year_from_release_date(album.get("release_date")),
                    duration_ms=t.get("duration_ms"),
                    isrc=(t.get("external_ids") or {}).get("isrc"),
                )
            )
            if limit and len(tracks) >= limit:
                return tracks
        if not res.get("next"):
            break
        offset += page
    return tracks


def fetch_artist_genres(
    sp: spotipy.Spotify,
    artist_ids: Iterable[str],
    cache=None,
    notify: Callable[[str], None] = print,
) -> dict[str, list[str]]:
    """Genres per artist, looked up one at a time.

    Spotify removed the several-artists endpoint in Feb 2026, so batching is no longer
    available. Each distinct artist is fetched once per run; with a cache supplied, once
    ever — which matters because this is ~50x the requests batching made.

    A lookup that fails is skipped rather than aborting the run: genre sources are
    best-effort, a track usually credits more than one artist, and with this many requests
    an occasional failure is expected. Failures are reported once so a broken source cannot
    masquerade as one that simply never matches.
    """
    unique = list({a for a in artist_ids if a})
    genres: dict[str, list[str]] = {}
    failed = 0
    for aid in unique:
        key = f"sp:artist:{aid}"
        cached = cache.get(key) if cache is not None else None
        if cached is not None:
            genres[aid] = cached
            continue
        try:
            artist = sp.artist(aid)
        except (SpotifyException, RequestException):
            # Only transport and API failures are tolerated. A blind catch would also
            # swallow our own parsing bugs and report them as "artist had no genres".
            failed += 1
            continue
        found = [g.lower() for g in (artist or {}).get("genres", [])]
        genres[aid] = found
        if cache is not None:
            cache.set(key, found)   # empty results cached too, so misses cost one lookup ever
    if failed:
        notify(f"spotify: {failed} of {len(unique)} artist lookups failed — those tracks may "
               f"resolve with fewer genres.")
    return genres


def attach_genres(tracks: list[Track], artist_genres: dict[str, list[str]]) -> None:
    """Populate each track's `genres` with the union of its artists' genres."""
    for t in tracks:
        seen: list[str] = []
        for aid in t.artist_ids:
            for g in artist_genres.get(aid, []):
                if g not in seen:
                    seen.append(g)
        t.genres = seen
