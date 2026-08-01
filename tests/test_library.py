import responses
import spotipy
from spotify_api import MockAPI, saved_track

from spotify_sorter.library import (
    Track,
    _year_from_release_date,
    attach_genres,
    fetch_artist_genres,
    fetch_liked_tracks,
)


def test_year_from_release_date():
    assert _year_from_release_date("1999-05-01") == 1999
    assert _year_from_release_date("2007") == 2007
    assert _year_from_release_date(None) is None
    assert _year_from_release_date("") is None
    assert _year_from_release_date("bad-date") is None


def _client():
    return spotipy.Spotify(auth="test-token")


@responses.activate
def test_fetch_liked_tracks_paginates_and_parses():
    saved = [saved_track(f"t{i}", year=1990 + i % 5) for i in range(120)]
    MockAPI(saved=saved).register()
    tracks = fetch_liked_tracks(_client())
    assert len(tracks) == 120
    t0 = tracks[0]
    assert t0.id == "t0" and t0.artist_ids == ["a1"] and t0.duration_ms == 200000
    assert 1990 <= t0.release_year <= 1994


@responses.activate
def test_fetch_liked_tracks_skips_local_and_respects_limit():
    saved = [saved_track("t1"), {"id": None, "name": "local"}, saved_track("t2")]
    MockAPI(saved=saved).register()
    assert [t.id for t in fetch_liked_tracks(_client())] == ["t1", "t2"]  # local skipped
    MockAPI(saved=saved).register()  # fresh registration for the second client call
    assert len(fetch_liked_tracks(_client(), limit=1)) == 1


@responses.activate
def test_fetch_artist_genres_batches_over_50():
    genres = {f"a{i}": [f"g{i}"] for i in range(130)}
    MockAPI(artist_genres=genres).register()
    got = fetch_artist_genres(_client(), [f"a{i}" for i in range(130)] + [None, ""])
    assert len(got) == 130 and got["a7"] == ["g7"]


def test_attach_genres_unions_across_artists():
    t = Track(id="x", name="n", artist_ids=["a1", "a2"], artist_names=["A", "B"], release_year=2000)
    attach_genres([t], {"a1": ["house", "deep house"], "a2": ["deep house", "techno"]})
    assert t.genres == ["house", "deep house", "techno"]  # de-duplicated, order preserved
