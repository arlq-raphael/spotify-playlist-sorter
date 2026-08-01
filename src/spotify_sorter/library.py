"""Read the user's Liked Songs and the genre data needed to classify them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import spotipy


@dataclass
class Track:
    id: str
    name: str
    artist_ids: list[str]
    artist_names: list[str]
    release_year: int | None
    duration_ms: int | None = None
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
                )
            )
            if limit and len(tracks) >= limit:
                return tracks
        if not res.get("next"):
            break
        offset += page
    return tracks


def fetch_artist_genres(sp: spotipy.Spotify, artist_ids: Iterable[str]) -> dict[str, list[str]]:
    """Batch-fetch genres for artists (Spotify allows 50 ids per request)."""
    unique = list({a for a in artist_ids if a})
    genres: dict[str, list[str]] = {}
    for i in range(0, len(unique), 50):
        batch = unique[i : i + 50]
        res = sp.artists(batch)
        for artist in res.get("artists", []):
            if artist and artist.get("id"):
                genres[artist["id"]] = [g.lower() for g in artist.get("genres", [])]
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
