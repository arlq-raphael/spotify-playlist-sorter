import os
import stat
from types import SimpleNamespace

import yaml

from spotify_sorter.config import Config
from spotify_sorter.configure import run_configure


def _args(**kw):
    base = {
        "prefix": None, "public": None, "providers": None, "decade_floor": None,
        "discogs_token": None, "spotify_client_id": None, "spotify_client_secret": None,
        "spotify_redirect": None, "force": False, "non_interactive": False,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_writes_only_changed_settings(tmp_path):
    cfg = tmp_path / "config.yaml"
    rc = run_configure(_args(non_interactive=True, prefix="My "),
                       config_path=cfg, creds_path=tmp_path / "creds")
    assert rc == 0
    assert yaml.safe_load(cfg.read_text()) == {"options": {"playlist_prefix": "My "}}
    # round-trip: user value + inherited defaults
    c = Config.load(str(cfg))
    assert c.playlist_prefix == "My "
    assert c.unmatched_genre_bucket == "Other"


def test_interactive_empty_answers_keep_defaults(tmp_path):
    cfg = tmp_path / "config.yaml"
    rc = run_configure(_args(), prompt=lambda *_: "", secret_prompt=lambda *_: "",
                       config_path=cfg, creds_path=tmp_path / "creds")
    assert rc == 0
    assert yaml.safe_load(cfg.read_text()) in (None, {})     # nothing changed


def test_secrets_go_to_credentials_not_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    creds = tmp_path / "creds"
    run_configure(
        _args(non_interactive=True, discogs_token="dtok",
              spotify_client_id="cid", spotify_client_secret="csec", spotify_redirect="uri"),
        config_path=cfg, creds_path=creds,
    )
    ctext = creds.read_text()
    assert "DISCOGS_TOKEN=dtok" in ctext
    assert "SPOTIPY_CLIENT_ID=cid" in ctext and "SPOTIPY_CLIENT_SECRET=csec" in ctext
    assert "dtok" not in cfg.read_text()                     # secret never in the YAML
    assert stat.S_IMODE(os.stat(creds).st_mode) == 0o600


def test_interactive_discogs_token_via_getpass(tmp_path):
    cfg = tmp_path / "config.yaml"
    creds = tmp_path / "creds"
    # prompts in order: prefix, public?, providers, floor, use-discogs?, spotify-creds?
    answers = iter(["", "", "", "", "y", "n"])
    run_configure(_args(), prompt=lambda *_: next(answers),
                  secret_prompt=lambda *_: "secrettok",
                  config_path=cfg, creds_path=creds)
    assert "DISCOGS_TOKEN=secrettok" in creds.read_text()


def test_non_interactive_all_flags(tmp_path):
    cfg = tmp_path / "config.yaml"
    run_configure(
        _args(non_interactive=True, prefix="P ", public=False,
              providers="spotify,discogs", decade_floor=1970),
        config_path=cfg, creds_path=tmp_path / "creds",
    )
    data = yaml.safe_load(cfg.read_text())
    assert data["options"]["playlist_prefix"] == "P "
    assert data["options"]["public_playlists"] is False
    assert data["genre_providers"] == ["spotify", "discogs"]
    assert data["decades"]["floor"] == 1970


def test_interactive_full_wizard(tmp_path):
    cfg = tmp_path / "config.yaml"
    creds = tmp_path / "creds"
    # prompts: prefix, public?, providers, floor, use-discogs?, spotify?, spotify-id, redirect
    answers = iter(["My ", "n", "spotify", "1980", "n", "y", "myid", ""])
    secrets = iter(["ssecret"])   # only the Spotify client secret uses getpass here
    run_configure(_args(), prompt=lambda *_: next(answers),
                  secret_prompt=lambda *_: next(secrets),
                  config_path=cfg, creds_path=creds)
    data = yaml.safe_load(cfg.read_text())
    assert data["options"] == {"playlist_prefix": "My ", "public_playlists": False}
    assert data["genre_providers"] == ["spotify"]
    assert data["decades"]["floor"] == 1980
    ctext = creds.read_text()
    assert "SPOTIPY_CLIENT_ID=myid" in ctext
    assert "SPOTIPY_CLIENT_SECRET=ssecret" in ctext
    assert "SPOTIPY_REDIRECT_URI=http://localhost:8888/callback" in ctext   # default kept


def test_interactive_floor_none(tmp_path):
    cfg = tmp_path / "config.yaml"
    answers = iter(["", "", "", "none", "n", "n"])
    run_configure(_args(), prompt=lambda *_: next(answers), secret_prompt=lambda *_: "",
                  config_path=cfg, creds_path=tmp_path / "creds")
    assert yaml.safe_load(cfg.read_text())["decades"]["floor"] is None


def test_interactive_floor_invalid_keeps_default(tmp_path):
    cfg = tmp_path / "config.yaml"
    answers = iter(["", "", "", "not-a-year", "n", "n"])
    run_configure(_args(), prompt=lambda *_: next(answers), secret_prompt=lambda *_: "",
                  config_path=cfg, creds_path=tmp_path / "creds")
    data = yaml.safe_load(cfg.read_text()) or {}
    assert "decades" not in data                     # invalid -> default 1950 -> not written


def test_overwrite_guard(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("{}\n")
    rc = run_configure(_args(non_interactive=True, prefix="X"),
                       config_path=cfg, creds_path=tmp_path / "creds")
    assert rc == 1
    assert cfg.read_text() == "{}\n"                         # untouched
    rc2 = run_configure(_args(non_interactive=True, prefix="X", force=True),
                        config_path=cfg, creds_path=tmp_path / "creds")
    assert rc2 == 0
    assert "X" in cfg.read_text()
