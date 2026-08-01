import os

import responses
import spotipy
from spotify_api import MockAPI, saved_track

import spotify_sorter.auth as auth_mod
from spotify_sorter.cli import _load_dotenv, main


def _use(monkeypatch, api: MockAPI):
    api.register()
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


def test_cli_no_command_shows_help():
    assert main([]) == 1


def test_load_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("FOO_TEST_VAR=bar\n# a comment\nNO_EQUALS_LINE\n")
    monkeypatch.delenv("FOO_TEST_VAR", raising=False)
    _load_dotenv()
    assert os.environ["FOO_TEST_VAR"] == "bar"
