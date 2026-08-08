"""Per-user credentials store for secrets, separate from the preferences config.

Mirrors the aws-cli split of ``~/.aws/config`` (preferences) from
``~/.aws/credentials`` (secrets). Secrets live in a flat ``KEY=VALUE`` file at
``~/.config/spotify-sorter/credentials`` (honoring ``$XDG_CONFIG_HOME``), written with
owner-only permissions. They are loaded into the process environment at startup so that
spotipy and the Discogs provider pick them up unchanged.

Recognized keys: ``DISCOGS_TOKEN``, ``SPOTIPY_CLIENT_ID``, ``SPOTIPY_CLIENT_SECRET``,
``SPOTIPY_REDIRECT_URI``.
"""
from __future__ import annotations

import os
from pathlib import Path


def credentials_path() -> Path:
    """The per-user credentials location, next to the config file."""
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "spotify-sorter" / "credentials"


def _strip_quotes(val: str) -> str:
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = _strip_quotes(val.strip())
    return out


def load_into_env(path: Path | None = None) -> None:
    """Load the credentials file into ``os.environ`` without overriding existing values.

    Uses ``setdefault`` so anything already set (real env var, or ``./.env`` loaded
    earlier) wins over the credentials file. A missing file is a no-op.
    """
    path = path or credentials_path()
    if not path.is_file():
        return
    for key, val in _parse(path.read_text(encoding="utf-8")).items():
        os.environ.setdefault(key, val)


def write_credential(key: str, value: str, path: Path | None = None) -> Path:
    """Upsert ``key=value`` in the credentials file, owner-only (0600).

    Replaces an existing line for ``key`` in place (preserving unrelated lines) or
    appends it. The file is created with mode 0600 from the start so the secret is
    never briefly world-readable.
    """
    path = path or credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    new_line = f"{key}={value}"
    replaced = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped.partition("=")[0].strip() == key:
            lines[i] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)

    # Create with 0600 from the outset (umask-independent); chmod an existing file too.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)
    return path
