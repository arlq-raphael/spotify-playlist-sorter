import responses
import spotipy
from spotify_api import MockAPI, saved_track

from spotify_sorter.config import Config
from spotify_sorter.dedupe import apply_removals
from spotify_sorter.sorter import Sorter


def _client():
    return spotipy.Spotify(auth="test-token")


def test_apply_removals_empty_is_noop():
    assert apply_removals(None, None, []) == ["nothing to remove"]


@responses.activate
def test_apply_removals_unsaves_and_purges_from_playlists():
    saved = [saved_track("keep"), saved_track("dropA"), saved_track("dropB")]
    playlists = {
        "p1": {"name": "Rock", "owner_id": "me", "tracks": ["keep", "dropA"]},
        "p2": {"name": "Jazz", "owner_id": "me", "tracks": ["dropB"]},
        "p3": {"name": "Untouched", "owner_id": "me", "tracks": ["keep"]},  # nothing to purge
    }
    api = MockAPI(saved=saved, playlists=playlists).register()
    sp = _client()
    actions = apply_removals(sp, Sorter(sp, Config.load()), ["dropA", "dropB"])

    assert {t["id"] for t in api.saved} == {"keep"}          # un-saved
    assert api.playlists["p1"]["tracks"] == ["keep"]         # purged from Rock
    assert api.playlists["p2"]["tracks"] == []               # purged from Jazz
    assert api.playlists["p3"]["tracks"] == ["keep"]         # skipped (no matches)
    assert any("un-saved 2" in a for a in actions)


@responses.activate
def test_apply_removals_dry_run_makes_no_changes():
    saved = [saved_track("keep"), saved_track("dropA")]
    playlists = {"p1": {"name": "Rock", "owner_id": "me", "tracks": ["keep", "dropA"]}}
    api = MockAPI(saved=saved, playlists=playlists).register()
    sp = _client()
    actions = apply_removals(sp, Sorter(sp, Config.load()), ["dropA"], dry_run=True)

    assert {t["id"] for t in api.saved} == {"keep", "dropA"}   # unchanged
    assert api.playlists["p1"]["tracks"] == ["keep", "dropA"]  # unchanged
    assert any("dry-run" in a for a in actions)
