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


def test_plan_add_dedupes_within_playlist():
    plan = Plan()
    plan.add("Rock", "t1")
    plan.add("Rock", "t1")  # same track twice -> kept once
    assert plan.by_playlist["Rock"] == ["t1"] and plan.total_placements == 1


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
def test_created_playlist_is_owned_by_the_authenticated_user():
    """Ownership is what makes idempotency hold: matching is restricted to playlists the
    user owns, so a playlist created under any other owner would never be matched again."""
    api = MockAPI(user_id="me").register()
    plan = Plan()
    plan.add("Rock", "t1")
    Sorter(_client(), Config.load()).apply(plan)
    created = next(p for p in api.playlists.values() if p["name"] == "Rock")
    assert created["owner_id"] == "me"


@responses.activate
def test_a_playlist_created_by_one_run_is_matched_by_the_next():
    """The guarantee the ownership clause protects — a second run must not duplicate."""
    api = MockAPI().register()
    plan = Plan()
    plan.add("Rock", "t1")
    sorter = Sorter(_client(), Config.load())

    sorter.apply(plan)
    assert [p["name"] for p in api.playlists.values()].count("Rock") == 1

    second = sorter.apply(plan)                      # same plan, fresh run
    assert [p["name"] for p in api.playlists.values()].count("Rock") == 1
    assert any("up to date" in a for a in second)     # matched, not recreated


@responses.activate
def test_creation_request_carries_visibility_from_config():
    """Asserts the flag is SENT, not that it takes effect.

    The double records what the request carried, so this catches us silently dropping the
    setting — previously impossible, since the double discarded it. It cannot show that a
    playlist ends up private: the live API ignores `public` on creation and returns a public
    playlist either way (#26). Naming this after the outcome would put a green test on a
    guarantee the platform is not honoring.
    """
    api = MockAPI().register()
    cfg = Config.load()
    cfg.public_playlists = False
    plan = Plan()
    plan.add("Private Bucket", "t1")
    Sorter(_client(), cfg).apply(plan)
    created = next(p for p in api.playlists.values() if p["name"] == "Private Bucket")
    assert created["public"] is False


@responses.activate
def test_apply_dry_run_changes_nothing():
    api = MockAPI().register()
    plan = Plan()
    plan.add("Rock", "t1")
    actions = Sorter(_client(), Config.load()).apply(plan, dry_run=True)
    assert any("[dry-run] CREATE" in a for a in actions)
    assert api.playlists == {}  # nothing created


@responses.activate
def test_apply_dry_run_add_to_existing_playlist():
    api = MockAPI(playlists={"p1": {"name": "Rock", "owner_id": "me", "tracks": ["old"]}}).register()
    plan = Plan()
    plan.add("Rock", "new1")
    actions = Sorter(_client(), Config.load()).apply(plan, dry_run=True)
    assert any("[dry-run] ADD" in a for a in actions)
    assert api.playlists["p1"]["tracks"] == ["old"]  # unchanged


@responses.activate
def test_existing_playlists_paginates_over_50():
    pls = {f"p{i}": {"name": f"N{i}", "owner_id": "me", "tracks": []} for i in range(120)}
    MockAPI(playlists=pls).register()
    assert len(Sorter(_client(), Config.load())._existing_playlists()) == 120


@responses.activate
def test_playlist_track_ids_paginates_over_100():
    tracks = [f"t{i}" for i in range(250)]
    MockAPI(playlists={"p1": {"name": "Big", "owner_id": "me", "tracks": tracks}}).register()
    assert len(Sorter(_client(), Config.load())._playlist_track_ids("p1")) == 250


@responses.activate
def test_existing_playlists_excludes_other_owners():
    MockAPI(playlists={
        "mine": {"name": "Mine", "owner_id": "me", "tracks": []},
        "theirs": {"name": "Theirs", "owner_id": "someone_else", "tracks": []},
    }).register()
    got = Sorter(_client(), Config.load())._existing_playlists()
    assert "Mine" in got and "Theirs" not in got
