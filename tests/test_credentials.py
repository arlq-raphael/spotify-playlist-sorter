import os
import stat

from spotify_sorter.cli import main
from spotify_sorter.credentials import credentials_path, load_into_env, write_credential


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def test_credentials_path_uses_xdg():
    p = credentials_path()
    assert p.name == "credentials" and p.parent.name == "spotify-sorter"


def test_write_credential_creates_0600():
    p = write_credential("DISCOGS_TOKEN", "tok")
    assert "DISCOGS_TOKEN=tok" in p.read_text()
    assert _mode(p) == 0o600


def test_write_credential_updates_in_place():
    write_credential("DISCOGS_TOKEN", "old")
    write_credential("SPOTIPY_CLIENT_ID", "id")
    p = write_credential("DISCOGS_TOKEN", "new")
    text = p.read_text()
    assert "DISCOGS_TOKEN=new" in text
    assert "DISCOGS_TOKEN=old" not in text
    assert "SPOTIPY_CLIENT_ID=id" in text          # unrelated line preserved
    assert text.count("DISCOGS_TOKEN=") == 1        # not duplicated
    assert _mode(p) == 0o600


def test_load_into_env_fills_unset():
    write_credential("DISCOGS_TOKEN", "fromfile")
    load_into_env()
    assert os.environ["DISCOGS_TOKEN"] == "fromfile"


def test_load_into_env_does_not_override(monkeypatch):
    write_credential("DISCOGS_TOKEN", "fromfile")
    monkeypatch.setenv("DISCOGS_TOKEN", "fromenv")
    load_into_env()
    assert os.environ["DISCOGS_TOKEN"] == "fromenv"    # env wins over the file


def test_dotenv_overrides_credentials_file_in_main(tmp_path, monkeypatch):
    """Full precedence: env > ./.env > credentials file.

    Exercised through main() so the *ordering* of the two loaders is what's under test —
    swapping those calls must fail here.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DISCOGS_TOKEN=fromdotenv\n")
    write_credential("DISCOGS_TOKEN", "fromcreds")
    assert main([]) == 1                                  # no command: loads both, prints help
    assert os.environ["DISCOGS_TOKEN"] == "fromdotenv"    # .env wins over credentials


def test_load_into_env_missing_file_is_noop(tmp_path):
    load_into_env(tmp_path / "no-such-credentials")    # must not raise


def test_load_into_env_strips_quotes_and_comments(tmp_path):
    p = tmp_path / "creds"
    p.write_text('# comment\nDISCOGS_TOKEN="quoted"\nNOEQUALS\n')
    load_into_env(p)
    assert os.environ["DISCOGS_TOKEN"] == "quoted"
