import pytest

import spotify_sorter.config as config_mod
from spotify_sorter.config import Config


def test_load_explicit_path(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("genre_buckets:\n  - name: X\n    match: [rock, indie]\n")
    c = Config.load(str(p))
    assert c.genre_buckets[0].name == "X" and c.genre_buckets[0].match == ["rock", "indie"]


def test_load_missing_path_raises():
    with pytest.raises(FileNotFoundError):
        Config.load("/nope/definitely-not-here.yaml")


def test_load_falls_back_to_cwd(monkeypatch, tmp_path):
    # Default packaged location missing -> fall back to ./config/genres.yaml
    monkeypatch.setattr(config_mod, "_DEFAULT_CONFIG", tmp_path / "missing.yaml")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "genres.yaml").write_text("genre_buckets: []\n")
    monkeypatch.chdir(tmp_path)
    assert Config.load().genre_buckets == []
