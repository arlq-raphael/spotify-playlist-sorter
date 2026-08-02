"""Install-shape guards.

The original bug shipped the default config *outside* the package with a `../config`
`package-data` escape setuptools silently drops, so wheels contained no config. These
deterministic checks (no build tooling / network needed) prevent that regression;
`test_config.test_packaged_default_resource_exists` additionally proves the resource
resolves via importlib.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def test_package_data_has_no_parent_escape():
    pyproject = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'data/*.yaml' in pyproject          # in-package glob that setuptools includes
    assert "../config" not in pyproject         # the old wheel-breaking escape is gone


def test_default_config_lives_inside_the_package():
    assert (_ROOT / "src" / "spotify_sorter" / "data" / "genres.yaml").is_file()


def test_no_toplevel_config_dir_remains():
    assert not (_ROOT / "config").exists()
