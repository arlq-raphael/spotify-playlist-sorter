from importlib.resources import files
from pathlib import Path

import pytest

from spotify_sorter.config import Config, _user_config_path


def _write_home(text: str) -> Path:
    """Write a user config at the (XDG-redirected) home location."""
    p = _user_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_load_explicit_path(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("genre_buckets:\n  - name: X\n    match: [rock, indie]\n")
    c = Config.load(str(p))
    assert c.genre_buckets[0].name == "X" and c.genre_buckets[0].match == ["rock", "indie"]


def test_load_missing_path_raises():
    with pytest.raises(FileNotFoundError):
        Config.load("/nope/definitely-not-here.yaml")


def test_load_uses_packaged_default():
    c = Config.load()
    assert c.genre_buckets                                    # non-empty, from the wheel resource
    assert c.genre_providers == ["musicbrainz", "discogs", "spotify"]


def test_packaged_default_resource_exists():
    assert (files("spotify_sorter") / "data" / "genres.yaml").is_file()


def test_user_config_deep_merges_over_bundled_defaults(tmp_path):
    p = tmp_path / "u.yaml"
    p.write_text("options:\n  playlist_prefix: 'X '\n")
    c = Config.load(str(p))
    assert c.playlist_prefix == "X "               # overridden
    assert c.unmatched_genre_bucket == "Other"     # inherited from the bundled default
    assert c.genre_buckets                          # inherited (non-empty)


# --- precedence chain: default -> home -> $SPOTIFY_SORTER_CONFIG -> --config ---

def test_home_config_discovered():
    _write_home("options:\n  playlist_prefix: 'HOME '\n")
    c = Config.load()
    assert c.playlist_prefix == "HOME "            # from the home config
    assert c.unmatched_genre_bucket == "Other"     # rest inherited


def test_missing_home_config_is_skipped():
    # No home config written -> load still succeeds from the packaged default.
    assert Config.load().genre_buckets


def test_xdg_config_home_respected(tmp_path, monkeypatch):
    alt = tmp_path / "altxdg"
    (alt / "spotify-sorter").mkdir(parents=True)
    (alt / "spotify-sorter" / "config.yaml").write_text("options:\n  playlist_prefix: 'ALT '\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(alt))
    assert Config.load().playlist_prefix == "ALT "


def test_env_var_config_layer(tmp_path, monkeypatch):
    _write_home("options:\n  playlist_prefix: 'HOME '\n  public_playlists: false\n")
    env_cfg = tmp_path / "env.yaml"
    env_cfg.write_text("options:\n  playlist_prefix: 'ENV '\n")
    monkeypatch.setenv("SPOTIFY_SORTER_CONFIG", str(env_cfg))
    c = Config.load()
    assert c.playlist_prefix == "ENV "             # env layer overrides home
    assert c.public_playlists is False              # still inherited from home


def test_flag_overrides_home_and_env(tmp_path, monkeypatch):
    _write_home("options:\n  playlist_prefix: 'HOME '\n")
    env_cfg = tmp_path / "env.yaml"
    env_cfg.write_text("options:\n  playlist_prefix: 'ENV '\n")
    monkeypatch.setenv("SPOTIFY_SORTER_CONFIG", str(env_cfg))
    flag_cfg = tmp_path / "flag.yaml"
    flag_cfg.write_text("options:\n  playlist_prefix: 'FLAG '\n")
    assert Config.load(str(flag_cfg)).playlist_prefix == "FLAG "   # flag wins


def test_env_config_missing_raises(monkeypatch):
    monkeypatch.setenv("SPOTIFY_SORTER_CONFIG", "/nope/env-config.yaml")
    with pytest.raises(FileNotFoundError):
        Config.load()


def test_defaults_ignores_user_layers():
    _write_home("options:\n  playlist_prefix: 'HOME '\n")
    assert Config.defaults().playlist_prefix == ""   # bundled default only, ignores home
