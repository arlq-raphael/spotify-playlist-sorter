"""Unit tests for classification — no Spotify credentials or network needed."""
import pytest

from spotify_sorter.classify import DecadeClassifier, GenreClassifier, build_classifiers
from spotify_sorter.config import Config
from spotify_sorter.library import Track


def test_build_classifiers_unknown_dimension_exits():
    with pytest.raises(SystemExit):
        build_classifiers(Config.load(), ["nonsense"])


def test_build_classifiers_respects_decades_disabled():
    cfg = Config.load()
    cfg.decades_enabled = False
    assert [c.dimension for c in build_classifiers(cfg, ["genre"])] == ["genre"]
    with pytest.raises(SystemExit):
        build_classifiers(cfg, ["decade"])  # disabled -> unavailable


def _track(genres=(), year=None):
    return Track(id="x", name="t", artist_ids=["a"], artist_names=["A"],
                 release_year=year, genres=list(genres))


def test_genre_first_match_wins_order():
    cfg = Config.load()  # default config
    g = GenreClassifier(cfg)
    # "dancehall" must win over generic "reggae" because Ragga bucket is listed first
    assert g.bucket(_track(["reggae", "dancehall"])) == "Ragga / Dancehall"
    assert g.bucket(_track(["roots reggae"])) == "Reggae Roots & Dub"


def test_genre_substring_matching():
    g = GenreClassifier(Config.load())
    assert g.bucket(_track(["french hip hop"])) == "French Rap"
    assert g.bucket(_track(["atlanta hip hop"])) == "Hip-Hop / Rap"
    assert g.bucket(_track(["deep house"])) == "House / Electro"


def test_genre_fallbacks():
    cfg = Config.load()
    g = GenreClassifier(cfg)
    # genres present but none configured -> unmatched bucket
    assert g.bucket(_track(["yodeling"])) == cfg.unmatched_genre_bucket
    # no genres at all -> no_genre bucket
    assert g.bucket(_track([])) == cfg.no_genre_bucket


def test_decade():
    d = DecadeClassifier(Config.load())
    assert d.bucket(_track(year=1994)) == "1990s"
    assert d.bucket(_track(year=2007)) == "2000s"
    assert d.bucket(_track(year=None)) is None
    # pre-floor years clamp to the floor decade (default floor 1950)
    assert d.bucket(_track(year=1948)) == "1950s"
