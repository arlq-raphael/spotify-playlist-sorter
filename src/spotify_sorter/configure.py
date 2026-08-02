"""The ``configure`` command: an interactive wizard that writes a minimal user config
and persists secrets to the credentials file.

Only settings changed from their defaults are written, so the generated config stays
minimal and keeps inheriting the bundled defaults. Secrets never go into the YAML — the
Discogs token and (optionally) the Spotify app credentials are written to the per-user
credentials file (0600) instead.
"""
from __future__ import annotations

import getpass
from pathlib import Path

import yaml

from .config import Config, _user_config_path
from .credentials import credentials_path, write_credential


def _ask(prompt, question: str, default: str) -> str:
    shown = f"{question} [{default}]: " if default != "" else f"{question} []: "
    answer = prompt(shown)
    # Blank input keeps the default; otherwise return the raw answer so a deliberate
    # trailing space (e.g. a playlist prefix like "🎧 ") is preserved.
    return answer if answer.strip() else default


def _ask_yes_no(prompt, question: str, default: bool) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    answer = prompt(f"{question} {hint}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def run_configure(
    args,
    *,
    prompt=input,
    secret_prompt=getpass.getpass,
    out=print,
    config_path: Path | None = None,
    creds_path: Path | None = None,
) -> int:
    """Collect settings + secrets and persist them. Returns a process exit code."""
    defaults = Config.defaults()
    config_path = Path(config_path) if config_path else _user_config_path()
    creds_path = Path(creds_path) if creds_path else credentials_path()
    interactive = not getattr(args, "non_interactive", False)

    if config_path.exists() and not getattr(args, "force", False):
        out(f"{config_path} already exists — pass --force to overwrite.")
        return 1

    # --- preferences (only changed-from-default values are persisted) ---
    prefix = args.prefix if args.prefix is not None else (
        _ask(prompt, "Playlist name prefix", defaults.playlist_prefix) if interactive
        else defaults.playlist_prefix
    )

    if args.public is not None:
        public = args.public
    elif interactive:
        public = _ask_yes_no(prompt, "Make playlists public?", defaults.public_playlists)
    else:
        public = defaults.public_playlists

    if args.providers is not None:
        providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    elif interactive:
        raw = _ask(prompt, "Genre sources (comma-separated)", ",".join(defaults.genre_providers))
        providers = [p.strip().lower() for p in raw.split(",") if p.strip()]
    else:
        providers = defaults.genre_providers

    floor = _resolve_floor(args, prompt, defaults, interactive)

    data: dict = {}
    if prefix != defaults.playlist_prefix:
        data.setdefault("options", {})["playlist_prefix"] = prefix
    if public != defaults.public_playlists:
        data.setdefault("options", {})["public_playlists"] = public
    if providers != defaults.genre_providers:
        data["genre_providers"] = providers
    if floor != defaults.decade_floor:
        data.setdefault("decades", {})["floor"] = floor

    config_path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(data, sort_keys=False) if data else "{}\n"
    config_path.write_text(
        "# spotify-sorter user config — only your customizations; the rest is inherited.\n"
        + body,
        encoding="utf-8",
    )
    out(f"Wrote {config_path}")

    # --- secrets (credentials file, never the YAML) ---
    _configure_secrets(args, prompt, secret_prompt, out, creds_path, interactive)
    return 0


def _resolve_floor(args, prompt, defaults, interactive):
    default_floor = defaults.decade_floor
    if args.decade_floor is not None:
        return args.decade_floor
    if not interactive:
        return default_floor
    raw = _ask(prompt, "Earliest decade (year, or 'none')", str(default_floor)).strip()
    if raw.lower() in ("none", "null", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        return default_floor


def _configure_secrets(args, prompt, secret_prompt, out, creds_path, interactive):
    wrote = []

    token = args.discogs_token
    if token is None and interactive and _ask_yes_no(prompt, "Use Discogs? (needs a token)", False):
        token = secret_prompt("  Discogs token: ").strip() or None
    if token:
        write_credential("DISCOGS_TOKEN", token, creds_path)
        wrote.append("DISCOGS_TOKEN")

    spotify = {
        "SPOTIPY_CLIENT_ID": args.spotify_client_id,
        "SPOTIPY_CLIENT_SECRET": args.spotify_client_secret,
        "SPOTIPY_REDIRECT_URI": args.spotify_redirect,
    }
    if not any(spotify.values()) and interactive and _ask_yes_no(
        prompt, "Set up Spotify app credentials?", False
    ):
        spotify["SPOTIPY_CLIENT_ID"] = prompt("  Spotify client id: ").strip() or None
        spotify["SPOTIPY_CLIENT_SECRET"] = secret_prompt("  Spotify client secret: ").strip() or None
        spotify["SPOTIPY_REDIRECT_URI"] = (
            prompt("  Redirect URI [http://localhost:8888/callback]: ").strip()
            or "http://localhost:8888/callback"
        )
    for key, val in spotify.items():
        if val:
            write_credential(key, val, creds_path)
            wrote.append(key)

    if wrote:
        out(f"Wrote {', '.join(wrote)} to {creds_path} (mode 600)")
