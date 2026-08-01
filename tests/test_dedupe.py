"""Unit tests for duplicate detection — no Spotify credentials or network needed."""
from spotify_sorter.dedupe import (
    choose_removals,
    classify,
    find_duplicates,
    group,
    normalize_key,
    version_tag,
)
from spotify_sorter.library import Track


def _t(tid, name, artist="A", dur=200000):
    return Track(id=tid, name=name, artist_ids=[artist], artist_names=[artist],
                 release_year=2000, duration_ms=dur)


def test_normalize_key_collapses_versions_and_credits():
    a = normalize_key("Hey Jude", "The Beatles")
    b = normalize_key("Hey Jude - Remastered 2009", "The Beatles")
    c = normalize_key("Hey Jude (feat. Someone)", "The Beatles")
    assert a == b == c


def test_version_tag_detection():
    assert version_tag("True - 2003 Remaster")
    assert version_tag("Mad About You - Live 2012")
    assert version_tag("Still Loving You") is None            # no " - " at all
    assert version_tag("Song - Interlude") is None            # " - " but not a version tag
    assert version_tag("Satta Massagana - Original Jamaican Mix")


def test_group_only_returns_duplicates():
    tracks = [_t("1", "Song X"), _t("2", "Song X"), _t("3", "Unique")]
    groups = group(tracks)
    assert len(groups) == 1 and len(groups[0]) == 2


def test_classify_exact_vs_version_pair():
    exact = [_t("1", "Song", dur=200000), _t("2", "Song", dur=201000)]  # within 3s
    assert classify(exact) == "exact"
    diff_dur = [_t("1", "Song", dur=200000), _t("2", "Song", dur=260000)]  # 60s apart
    assert classify(diff_dur) == "version_pair"
    tagged = [_t("1", "Song", dur=200000), _t("2", "Song - Remaster", dur=200000)]
    assert classify(tagged) == "version_pair"


def test_choose_removals_exact_keeps_one():
    g = [_t("1", "Song"), _t("2", "Song")]
    keep, remove, unresolved = choose_removals(g, "exact")
    assert keep == "1" and remove == ["2"] and unresolved is False


def test_choose_removals_version_pair_keeps_untagged_original():
    g = [_t("1", "Song"), _t("2", "Song - Remastered 2011")]
    keep, remove, unresolved = choose_removals(g, "version_pair")
    assert keep == "1" and remove == ["2"] and unresolved is False


def test_choose_removals_original_tag_wins():
    g = [_t("1", "Satta Massagana"),
         _t("2", "Satta Massagana - Original Jamaican Mix")]
    keep, remove, _ = choose_removals(g, "version_pair")
    assert keep == "2" and remove == ["1"]


def test_choose_removals_unresolved_when_both_tagged():
    g = [_t("1", "Song - Remix"), _t("2", "Song - Radio Edit")]
    keep, remove, unresolved = choose_removals(g, "version_pair")
    assert unresolved is True and keep is None and remove == []


def test_find_duplicates_end_to_end():
    tracks = [
        _t("1", "Song A", dur=200000),
        _t("2", "Song A", dur=200500),                 # exact dup of 1
        _t("3", "Song B"),
        _t("4", "Song B - Live", dur=260000),          # version pair with 3
        _t("5", "Only Once"),
    ]
    groups = {tuple(sorted(t.id for t in g.tracks)): g for g in find_duplicates(tracks)}
    assert groups[("1", "2")].kind == "exact"
    assert groups[("3", "4")].kind == "version_pair"
    assert groups[("3", "4")].keep_id == "3"
