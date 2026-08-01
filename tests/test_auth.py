import pytest
import spotipy

from spotify_sorter.auth import SCOPES, get_client


def test_get_client_missing_env_exits(monkeypatch):
    for v in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(SystemExit):
        get_client()


def test_get_client_builds_with_env(monkeypatch):
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "x")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "y")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    client = get_client()  # construction only — no network / no browser until a request
    assert isinstance(client, spotipy.Spotify)


def test_scopes_include_library_modify_for_dedupe():
    assert "user-library-modify" in SCOPES
