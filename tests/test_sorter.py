import responses
import spotipy
from spotify_api import MockAPI

from spotify_sorter.classify import build_classifiers
from spotify_sorter.config import Config
from spotify_sorter.library import Track
from spotify_sorter.sorter import Plan, Sorter


def _client():
    return spotipy.Spotify(auth="test-token")


def _track(tid, genres=(), year=2000):
    return Track(id=tid, name="n", artist_ids=["a"], artist_names=["A"],
                 release_year=year, genres=list(genres))


def test_plan_places_by_genre_and_decade():
    cfg = Config.load()
    classifiers = build_classifiers(cfg, ["genre", "decade"])
    tracks = [_track("t1", ["deep house"], 2001), _track("t2", ["reggae"], 1978)]
    plan = Sorter(None, cfg).plan(tracks, classifiers)  # planning needs no network
    assert "House / Electro" in plan.by_playlist
    assert "2000s" in plan.by_playlist and "1970s" in plan.by_playlist
    assert plan.total_placements == 4


def test_plan_records_skips():
    cfg = Config.load()
    # decade-only classifier + a track with no release year -> skipped
    classifiers = build_classifiers(cfg, ["decade"])
    plan = Sorter(None, cfg).plan([_track("t", year=None)], classifiers)
    assert plan.total_placements == 0 and len(plan.skipped_tracks) == 1


@responses.activate
def test_apply_creates_then_is_idempotent():
    api = MockAPI().register()
    sorter = Sorter(_client(), Config.load())
    plan = Plan()
    plan.add("Rock", "t1")
    plan.add("Rock", "t2")
    plan.add("Jazz", "t3")

    first = sorter.apply(plan)
    assert any("CREATE playlist 'Rock'" in a for a in first)
    names = {p["name"]: p["tracks"] for p in api.playlists.values()}
    assert names["Rock"] == ["t1", "t2"] and names["Jazz"] == ["t3"]

    second = sorter.apply(plan)  # nothing new to add
    assert all("up to date" in a for a in second)


@responses.activate
def test_apply_dry_run_changes_nothing():
    api = MockAPI().register()
    plan = Plan()
    plan.add("Rock", "t1")
    actions = Sorter(_client(), Config.load()).apply(plan, dry_run=True)
    assert any("[dry-run] CREATE" in a for a in actions)
    assert api.playlists == {}  # nothing created


@responses.activate
def test_existing_playlists_excludes_other_owners():
    MockAPI(playlists={
        "mine": {"name": "Mine", "owner_id": "me", "tracks": []},
        "theirs": {"name": "Theirs", "owner_id": "someone_else", "tracks": []},
    }).register()
    got = Sorter(_client(), Config.load())._existing_playlists()
    assert "Mine" in got and "Theirs" not in got
