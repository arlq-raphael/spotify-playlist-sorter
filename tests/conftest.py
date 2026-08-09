"""Global test isolation.

Point `$XDG_CONFIG_HOME` at a per-test temp dir so config/credential lookups never
touch the developer's real `~/.config`, and clear the secret/config env vars so a
developer machine with `DISCOGS_TOKEN` (etc.) exported can't leak into tests.

The genre cache needs the same treatment. Its default path is `.genre-cache.json`,
resolved against the working directory — so without this, every test that runs the CLI
writes into the repo root and reads back what an earlier test left there. That is not
hypothetical: it produced a cross-test failure where one test's artist genres decided
another test's playlist. Redirecting it per-test keeps runs independent and stops the
suite littering the checkout.
"""
import pytest
import yaml


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

    # Layered above the packaged default, so it only overrides the cache location.
    cfg = tmp_path / "isolated-config.yaml"
    cfg.write_text(yaml.safe_dump({"cache": {"path": str(tmp_path / "genre-cache.json")}}))
    monkeypatch.setenv("SPOTIFY_SORTER_CONFIG", str(cfg))
    yield
