import os

import responses
import spotipy
from spotify_api import MockAPI, saved_track

import spotify_sorter.auth as auth_mod
from spotify_sorter.cli import _load_dotenv, main


def _use(monkeypatch, api: MockAPI):
    api.register()
    monkeypatch.delenv("DISCOGS_TOKEN", raising=False)  # keep the Discogs provider skipped in CLI tests
    sp = spotipy.Spotify(auth="test-token")
    monkeypatch.setattr(auth_mod, "get_client", lambda: sp)
    return sp


@responses.activate
def test_cli_sort_dry_run(monkeypatch, capsys):
    _use(monkeypatch, MockAPI(saved=[saved_track("t1", year=2001)],
                              artist_genres={"a1": ["deep house"]}))
    assert main(["sort", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "House / Electro" in out and "Dry run complete" in out


@responses.activate
def test_cli_sort_applies(monkeypatch):
    api = MockAPI(saved=[saved_track("t1", year=2001)], artist_genres={"a1": ["techno"]})
    _use(monkeypatch, api)
    assert main(["sort", "-d", "genre", "decade"]) == 0
    names = {p["name"] for p in api.playlists.values()}
    assert "Techno / EDM" in names and "2000s" in names


@responses.activate
def test_cli_dedupe_report_then_apply(monkeypatch):
    api = MockAPI(saved=[saved_track("k", "Song"), saved_track("d", "Song")])
    _use(monkeypatch, api)
    assert main(["dedupe"]) == 0          # report only
    assert len(api.saved) == 2            # unchanged
    assert main(["dedupe", "--apply"]) == 0
    assert len(api.saved) == 1            # redundant copy removed


@responses.activate
def test_cli_auth(monkeypatch, capsys):
    _use(monkeypatch, MockAPI())
    assert main(["auth"]) == 0
    assert "Authenticated" in capsys.readouterr().out


@responses.activate
def test_cli_sort_decade_only_reports_skips(monkeypatch, capsys):
    # a track with no parseable release year -> skipped when sorting by decade only
    no_year = {"id": "t1", "name": "n", "artists": [{"id": "a1", "name": "A"}],
               "album": {"release_date": ""}, "duration_ms": 200000}
    _use(monkeypatch, MockAPI(saved=[no_year]))
    assert main(["sort", "-d", "decade", "--dry-run"]) == 0
    assert "matched no dimension" in capsys.readouterr().out


@responses.activate
def test_cli_dedupe_reports_pairs_and_unresolved(monkeypatch, capsys):
    saved = [
        saved_track("a", "Song"), saved_track("b", "Song - Remastered 2011"),  # resolved pair
        saved_track("c", "Tune - Remix"), saved_track("d", "Tune - Radio Edit"),  # unresolved
    ]
    _use(monkeypatch, MockAPI(saved=saved))
    assert main(["dedupe"]) == 0
    out = capsys.readouterr().out
    assert "Version pairs" in out and "Unresolved" in out


@responses.activate
def test_cli_dedupe_no_duplicates(monkeypatch, capsys):
    _use(monkeypatch, MockAPI(saved=[saved_track("a", "One"), saved_track("b", "Two")]))
    assert main(["dedupe"]) == 0
    assert "0 redundant copies" in capsys.readouterr().out


def test_cli_no_command_shows_help():
    assert main([]) == 1


def test_main_module_is_importable():
    import importlib
    assert importlib.import_module("spotify_sorter.__main__") is not None


def test_load_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO_TEST_VAR=bar\n# a comment\nNO_EQUALS_LINE\n")
    monkeypatch.delenv("FOO_TEST_VAR", raising=False)
    _load_dotenv()
    assert os.environ["FOO_TEST_VAR"] == "bar"
