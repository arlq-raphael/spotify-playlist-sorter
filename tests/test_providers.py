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


@responses.activate
def test_one_artist_shared_by_many_tracks_is_fetched_once():
    """Spec: a distinct artist is looked up at most once per run, however many tracks credit it."""
    saved = [saved_track(f"t{i}", artists=(("a1", "Artist"),)) for i in range(5)]
    MockAPI(saved=saved, artist_genres={"a1": ["dub"]}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)
    out = SpotifyGenreProvider(sp).genres_for(tracks)
    assert out == {f"t{i}": ["dub"] for i in range(5)}
    lookups = [c for c in responses.calls if "/artists/" in c.request.url]
    assert len(lookups) == 1


@responses.activate
def test_track_with_several_artists_combines_in_credit_order():
    MockAPI(saved=[saved_track("t1", artists=(("a1", "A"), ("a2", "B")))],
            artist_genres={"a1": ["dub", "reggae"], "a2": ["reggae", "ska"]}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)
    # credit order preserved, no repeats
    assert SpotifyGenreProvider(sp).genres_for(tracks) == {"t1": ["dub", "reggae", "ska"]}


@responses.activate
def test_a_failing_artist_lookup_skips_that_artist_and_reports_once(tmp_path):
    """Design decision: best-effort, like every other source. With ~50x the requests,
    inheriting 'any error aborts the run' would have multiplied #18's blast radius."""
    MockAPI(saved=[saved_track("t1", artists=(("a1", "A"), ("bad", "B")))],
            artist_genres={"a1": ["jazz"]},
            artist_errors={"bad": 500}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)
    notices = []
    out = SpotifyGenreProvider(sp, notify=notices.append).genres_for(tracks)
    assert out == {"t1": ["jazz"]}          # the working artist still contributes
    assert len(notices) == 1                 # reported, not swallowed
    assert "failed" in notices[0]


@responses.activate
def test_artist_genres_are_cached_across_runs(tmp_path):
    from spotify_sorter.cache import GenreCache
    path = str(tmp_path / "c.json")
    MockAPI(saved=[saved_track("t1")], artist_genres={"a1": ["techno"]}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)

    run1 = GenreCache(path)
    SpotifyGenreProvider(sp, cache=run1).genres_for(tracks)
    run1.save()
    first = len([c for c in responses.calls if "/artists/" in c.request.url])

    run2 = GenreCache(path)                  # fresh cache loaded from disk
    out = SpotifyGenreProvider(sp, cache=run2).genres_for(tracks)
    assert out == {"t1": ["techno"]}
    after = len([c for c in responses.calls if "/artists/" in c.request.url])
    assert first == 1 and after == 1         # second run made no artist request


@responses.activate
def test_an_artist_with_no_genres_is_remembered(tmp_path):
    from spotify_sorter.cache import GenreCache
    path = str(tmp_path / "c.json")
    MockAPI(saved=[saved_track("t1")], artist_genres={}).register()   # a1 has no genres
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)

    run1 = GenreCache(path)
    SpotifyGenreProvider(sp, cache=run1).genres_for(tracks)
    run1.save()
    run2 = GenreCache(path)
    SpotifyGenreProvider(sp, cache=run2).genres_for(tracks)
    lookups = [c for c in responses.calls if "/artists/" in c.request.url]
    assert len(lookups) == 1                 # the empty result was not re-queried


@responses.activate
def test_the_batch_endpoint_is_not_used():
    """Guard: the removed endpoint must never be reached, whatever the artist count."""
    saved = [saved_track(f"t{i}", artists=((f"a{i}", "X"),)) for i in range(60)]
    MockAPI(saved=saved, artist_genres={f"a{i}": ["pop"] for i in range(60)}).register()
    sp = spotipy.Spotify(auth="test-token")
    tracks = fetch_liked_tracks(sp)
    SpotifyGenreProvider(sp).genres_for(tracks)
    assert not [c for c in responses.calls if "ids=" in c.request.url]
    assert len([c for c in responses.calls if "/artists/" in c.request.url]) == 60


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
