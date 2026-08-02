"""Global test isolation.

Point `$XDG_CONFIG_HOME` at a per-test temp dir so config/credential lookups never
touch the developer's real `~/.config`, and clear the secret/config env vars so a
developer machine with `DISCOGS_TOKEN` (etc.) exported can't leak into tests.
"""
import pytest


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for var in (
        "DISCOGS_TOKEN",
        "SPOTIFY_SORTER_CONFIG",
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
    ):
        monkeypatch.delenv(var, raising=False)
    yield
