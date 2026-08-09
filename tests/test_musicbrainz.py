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
def test_client_retries_once_on_503_at_the_isrc_step(monkeypatch):
    monkeypatch.setattr(mb_mod.time, "sleep", lambda *_: None)  # don't actually wait
    state = {"n": 0}

    def isrc_cb(request):
        state["n"] += 1
        if state["n"] == 1:
            return 503, {}, "{}"
        return 200, {}, json.dumps({"isrc": "X", "recordings": [{"id": "mb1"}]})

    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/"), callback=isrc_cb
    )
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/recording/"),
        callback=lambda r: (200, {}, json.dumps({"genres": [{"name": "Soul"}]})),
    )
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("X") == ["soul"]
    assert state["n"] == 2  # retried after the 503


@responses.activate
def test_client_retries_once_on_503_at_the_recording_step(monkeypatch):
    """The retry must cover both lookups, not just the first."""
    monkeypatch.setattr(mb_mod.time, "sleep", lambda *_: None)
    state = {"n": 0}

    def recording_cb(request):
        state["n"] += 1
        if state["n"] == 1:
            return 503, {}, "{}"
        return 200, {}, json.dumps({"genres": [{"name": "Dub"}]})

    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/"),
        callback=lambda r: (200, {}, json.dumps({"isrc": "X", "recordings": [{"id": "mb1"}]})),
    )
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/recording/"),
        callback=recording_cb,
    )
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("X") == ["dub"]
    assert state["n"] == 2


@responses.activate
def test_isrc_with_several_recordings_uses_the_first_only():
    """Spec: the first recording identified is used; the others are not merged in."""
    mock_musicbrainz({"ISRC1": [["techno"], ["dub", "reggae"]]})
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("ISRC1") == ["techno"]
    fetched = [c for c in responses.calls if "/recording/" in c.request.url]
    assert len(fetched) == 1  # cost stays at one recording per track


@responses.activate
def test_identified_recording_without_genres_yields_empty(tmp_path):
    """Falls through to the next source, and the empty result is still cached."""
    mock_musicbrainz({"ISRC1": []})
    cache = GenreCache(str(tmp_path / "c.json"))
    provider = MusicBrainzGenreProvider("ua", cache, min_interval=0)
    assert provider.genres_for([_track("t1", isrc="ISRC1")]) == {}   # nothing resolved

    before = len(responses.calls)
    provider.genres_for([_track("t1", isrc="ISRC1")])                # second pass
    assert len(responses.calls) == before                            # served from cache


@responses.activate
def test_recording_404_returns_empty():
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/"),
        callback=lambda r: (200, {}, json.dumps({"isrc": "X", "recordings": [{"id": "gone"}]})),
    )
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/recording/"),
        callback=lambda r: (404, {}, json.dumps({"error": "Not Found"})),
    )
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("X") == []


@responses.activate
def test_isrc_without_a_usable_recording_skips_the_second_lookup():
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/"),
        callback=lambda r: (200, {}, json.dumps({"isrc": "X", "recordings": []})),
    )
    assert MusicBrainzClient("ua", min_interval=0).genres_for_isrc("X") == []
    assert not [c for c in responses.calls if "/recording/" in c.request.url]


@responses.activate
def test_every_request_is_paced_not_every_track():
    """Two requests per lookup means two waits — pacing per track would query at 2x."""
    mock_musicbrainz({"ISRC1": ["techno"]})
    client = MusicBrainzClient("ua", min_interval=0)
    seen = {"n": 0}
    original = client._throttle

    def counting():
        seen["n"] += 1
        original()

    client._throttle = counting
    client.genres_for_isrc("ISRC1")
    assert seen["n"] == 2


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
