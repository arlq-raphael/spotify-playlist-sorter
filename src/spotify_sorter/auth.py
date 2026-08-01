"""Spotify authentication (OAuth Authorization Code flow via spotipy)."""
from __future__ import annotations

import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Scopes: read the library, read + modify (public and private) playlists.
SCOPES = (
    "user-library-read "
    "user-library-modify "  # needed by `dedupe` to un-save redundant copies
    "playlist-read-private "
    "playlist-modify-public "
    "playlist-modify-private"
)


def get_client() -> spotipy.Spotify:
    """Build an authenticated Spotify client.

    Reads SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET / SPOTIPY_REDIRECT_URI from
    the environment (see .env.example). On first run this opens a browser to
    authorize; the token is then cached in .cache for subsequent runs.
    """
    missing = [
        v for v in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
        if not os.environ.get(v)
    ]
    if missing:
        raise SystemExit(
            "Missing environment variables: " + ", ".join(missing) + "\n"
            "Copy .env.example to .env and fill it in (or export them). See the README."
        )
    auth = SpotifyOAuth(scope=SCOPES, open_browser=True)
    # retries: spotipy honours Spotify's Retry-After on 429 automatically.
    return spotipy.Spotify(auth_manager=auth, retries=5, status_retries=5, backoff_factor=0.5)
