import pytest
import responses
import spotipy
from spotify_api import MockAPI, saved_track

from spotify_sorter.config import Config
from spotify_sorter.library import Track, fetch_liked_tracks
from spotify_sorter.providers import SpotifyGenreProvider, build_providers, resolve_genres


class FakeProvider:
    def __init__(self, name, mapping):
        self.name = name
        self.mapping = mapping

    def genres_for(self, tracks):
        return {t.id: list(self.mapping.get(t.id, [])) for t in tracks}


def _t(tid):
    return Track(id=tid, name="n", artist_ids=["a"], artist_names=["A"], release_year=2000)


def test_resolve_first_non_empty_wins():
    tracks = [_t("t1"), _t("t2")]
    p1 = FakeProvider("p1", {"t1": ["house"]})            # resolves t1 only
    p2 = FakeProvider("p2", {"t1": ["ignored"], "t2": ["reggae"]})
    resolved = resolve_genres(tracks, [p1, p2])
    assert resolved == {"t1": ["house"], "t2": ["reggae"]}
    assert tracks[0].genres == ["house"]                  # p2 not used for t1


def test_resolve_no_provider_leaves_empty():
    tracks = [_t("t1")]
    resolve_genres(tracks, [FakeProvider("p", {})])
    assert tracks[0].genres == []


@responses.activate
def test_spotify_provider_unions_artist_genres():
    MockAPI(saved=[saved_track("t1")], artist_genres={"a1": ["deep house", "techno"]}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)
    assert SpotifyGenreProvider(sp).genres_for(tracks) == {"t1": ["deep house", "techno"]}


def test_build_providers_unknown_name_exits():
    cfg = Config.load()
    cfg.genre_providers = ["bogus"]
    with pytest.raises(SystemExit):
        build_providers(cfg, sp=None, cache=None)


def test_build_providers_skips_discogs_without_token(monkeypatch):
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)
    cfg = Config.load()
    cfg.genre_providers = ["discogs", "spotify"]
    notes = []
    providers = build_providers(cfg, sp="SP", cache=None, notify=notes.append)
    assert [p.name for p in providers] == ["spotify"]     # discogs skipped
    assert any("DISCOGS_TOKEN" in n for n in notes)
