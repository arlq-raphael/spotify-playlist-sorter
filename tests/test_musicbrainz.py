import json
import re

import responses
from spotify_api import mock_musicbrainz

import spotify_sorter.musicbrainz as mb_mod
from spotify_sorter.cache import GenreCache
from spotify_sorter.library import Track
from spotify_sorter.musicbrainz import MusicBrainzClient, MusicBrainzGenreProvider


def _track(tid, isrc=None):
    return Track(id=tid, name="n", artist_ids=["a"], artist_names=["A"], release_year=2000, isrc=isrc)


@responses.activate
def test_client_genres_for_isrc():
    mock_musicbrainz({"ISRC1": ["deep house", "electronic"]})
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("ISRC1") == \
        ["deep house", "electronic"]


@responses.activate
def test_client_404_returns_empty():
    mock_musicbrainz({})  # any ISRC -> 404
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("NOPE") == []


@responses.activate
def test_client_throttles_between_calls():
    mock_musicbrainz({"A": ["x"], "B": ["y"]})
    client = MusicBrainzClient("ua", min_interval=0.01)  # tiny, exercises the wait branch
    client.genres_for_isrc("A")
    assert client.genres_for_isrc("B") == ["y"]


@responses.activate
def test_client_retries_once_on_503(monkeypatch):
    monkeypatch.setattr(mb_mod.time, "sleep", lambda *_: None)  # don't actually wait
    state = {"n": 0}

    def cb(request):
        state["n"] += 1
        if state["n"] == 1:
            return 503, {}, "{}"
        return 200, {}, json.dumps({"recordings": [{"genres": [{"name": "Soul"}]}]})

    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/"), callback=cb
    )
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("X") == ["soul"]
    assert state["n"] == 2  # retried after the 503


@responses.activate
def test_provider_resolves_isrc_and_skips_without(tmp_path):
    mock_musicbrainz({"ISRC1": ["techno"]})
    provider = MusicBrainzGenreProvider("ua", GenreCache(str(tmp_path / "c.json")), min_interval=0)
    out = provider.genres_for([_track("t1", isrc="ISRC1"), _track("t2", isrc=None)])
    assert out == {"t1": ["techno"]}  # t2 has no ISRC -> skipped


@responses.activate
def test_persistent_cache_reused_across_runs(tmp_path):
    mock_musicbrainz({"ISRC1": ["dub"]})
    path = str(tmp_path / "c.json")

    run1 = GenreCache(path)
    MusicBrainzGenreProvider("ua", run1, min_interval=0).genres_for([_track("t1", isrc="ISRC1")])
    run1.save()

    run2 = GenreCache(path)  # fresh cache loaded from disk
    out = MusicBrainzGenreProvider("ua", run2, min_interval=0).genres_for([_track("t1", isrc="ISRC1")])
    assert out == {"t1": ["dub"]}

    isrc_calls = [c for c in responses.calls if "/isrc/" in c.request.url]
    assert len(isrc_calls) == 1  # second run served entirely from the persisted cache
