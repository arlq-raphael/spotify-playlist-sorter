"""Ordered genre providers: resolve each track's genres from configured sources.

Providers are consulted in order; the first to return a non-empty genre set for a
track wins, and later providers are only asked about still-unresolved tracks.
"""
from __future__ import annotations

from typing import Callable, Protocol

from .config import Config
from .library import Track, fetch_artist_genres


class GenreProvider(Protocol):
    name: str

    def genres_for(self, tracks: list[Track]) -> dict[str, list[str]]:
        """Return {track_id: genres} for the tracks this provider could resolve."""
        ...


def resolve_genres(tracks: list[Track], providers: list[GenreProvider]) -> dict[str, list[str]]:
    """Fill each track's ``genres`` from the first provider that resolves it."""
    resolved: dict[str, list[str]] = {}
    for provider in providers:
        pending = [t for t in tracks if t.id not in resolved]
        if not pending:
            break
        for track_id, genres in provider.genres_for(pending).items():
            if genres:
                resolved[track_id] = genres
    for t in tracks:
        t.genres = resolved.get(t.id, [])
    return resolved


class SpotifyGenreProvider:
    name = "spotify"

    def __init__(self, sp):
        self.sp = sp

    def genres_for(self, tracks: list[Track]) -> dict[str, list[str]]:
        artist_genres = fetch_artist_genres(self.sp, [a for t in tracks for a in t.artist_ids])
        out: dict[str, list[str]] = {}
        for t in tracks:
            genres: list[str] = []
            for aid in t.artist_ids:
                for g in artist_genres.get(aid, []):
                    if g not in genres:
                        genres.append(g)
            out[t.id] = genres
        return out


def build_providers(
    config: Config, sp, cache, notify: Callable[[str], None] = print
) -> list[GenreProvider]:
    """Instantiate the providers named in ``config.genre_providers``, in order."""
    providers: list[GenreProvider] = []
    for name in config.genre_providers:
        if name == "spotify":
            providers.append(SpotifyGenreProvider(sp))
        elif name == "musicbrainz":
            from .musicbrainz import MusicBrainzGenreProvider

            providers.append(MusicBrainzGenreProvider(config.musicbrainz_user_agent, cache))
        elif name == "discogs":
            from .discogs import build_discogs_provider

            provider = build_discogs_provider(config, cache, notify)
            if provider is not None:  # skipped when no DISCOGS_TOKEN
                providers.append(provider)
        else:
            raise SystemExit(
                f"Unknown genre provider: {name!r} (known: spotify, discogs, musicbrainz)"
            )
    return providers
