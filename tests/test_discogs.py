import discogs_client
import responses
from spotify_api import mock_discogs

from spotify_sorter.cache import GenreCache
from spotify_sorter.config import Config
from spotify_sorter.discogs import DiscogsGenreProvider, build_discogs_provider
from spotify_sorter.library import Track


def _track(tid, name="Song", artist="Artist"):
    return Track(id=tid, name=name, artist_ids=["a"], artist_names=[artist], release_year=2000)


def _client():
    return discogs_client.Client("ua/test", user_token="tok")


@responses.activate
def test_returns_genre_and_style(tmp_path):
    mock_discogs({"artist|song": {"genre": ["Electronic"], "style": ["Deep House"]}})
    provider = DiscogsGenreProvider(_client(), GenreCache(str(tmp_path / "c.json")))
    assert provider.genres_for([_track("t1")]) == {"t1": ["electronic", "deep house"]}


@responses.activate
def test_no_match_caches_empty(tmp_path):
    mock_discogs({})  # no results for anything
    cache = GenreCache(str(tmp_path / "c.json"))
    assert DiscogsGenreProvider(_client(), cache).genres_for([_track("t1")]) == {}
    assert cache.get("dg:artist|song") == []  # miss is cached to avoid re-querying


@responses.activate
def test_caches_same_query(tmp_path):
    mock_discogs({"artist|song": {"genre": ["Rock"], "style": []}})
    provider = DiscogsGenreProvider(_client(), GenreCache(str(tmp_path / "c.json")))
    provider.genres_for([_track("t1")])
    provider.genres_for([_track("t2")])  # same artist|title
    searches = [c for c in responses.calls if "database/search" in c.request.url]
    assert len(searches) == 1


def test_build_skips_without_token(monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    notes = []
    assert build_discogs_provider(Config.load(), cache=None, notify=notes.append) is None
    assert any("DISCOGS_TOKEN" in n for n in notes)


def test_build_with_token_returns_provider(monkeypatch):
    monkeypatch.setenv("DISCOGS_TOKEN", "tok")
    provider = build_discogs_provider(Config.load(), cache=None)
    assert isinstance(provider, DiscogsGenreProvider)
