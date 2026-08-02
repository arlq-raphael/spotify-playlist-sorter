from spotify_sorter.cache import GenreCache


def test_roundtrip_persists(tmp_path):
    p = tmp_path / "c.json"
    c = GenreCache(str(p))
    c.set("k", ["a", "b"])
    c.save()
    assert GenreCache(str(p)).get("k") == ["a", "b"]


def test_save_noop_when_clean(tmp_path):
    p = tmp_path / "c.json"
    GenreCache(str(p)).save()  # nothing set -> not dirty -> no file written
    assert not p.exists()


def test_corrupt_file_ignored(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{ not valid json")
    assert GenreCache(str(p)).data == {}


def test_non_dict_file_ignored(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("[1, 2, 3]")
    assert GenreCache(str(p)).data == {}


def test_load_and_save_errors_are_swallowed(tmp_path):
    # Pointing at a directory makes both read_text (init) and write_text (save) raise OSError.
    d = tmp_path / "a_dir"
    d.mkdir()
    c = GenreCache(str(d))     # read_text on a dir -> OSError swallowed -> empty
    assert c.data == {}
    c.set("k", [])
    c.save()                   # write_text on a dir -> OSError swallowed, no crash
