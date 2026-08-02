"""Command-line interface: `spotify-sorter sort [--dimensions genre decade]`."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (avoids a python-dotenv dependency)."""
    env = Path(".env")
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="spotify-sorter",
        description="Sort your Spotify Liked Songs into per-genre and per-decade playlists.",
    )
    sub = p.add_subparsers(dest="command")

    sort = sub.add_parser("sort", help="Classify Liked Songs and update playlists.")
    sort.add_argument(
        "--dimensions", "-d", nargs="+", default=["genre", "decade"],
        help="Which dimensions to sort by (default: genre decade).",
    )
    sort.add_argument("--config", "-c", default=None, help="Path to a genres.yaml config.")
    sort.add_argument("--limit", "-n", type=int, default=None,
                      help="Only process the N most-recent liked songs (for testing).")
    sort.add_argument("--dry-run", action="store_true",
                      help="Show what would change without modifying anything.")

    dd = sub.add_parser("dedupe", help="Find (and optionally remove) duplicate Liked Songs.")
    dd.add_argument("--apply", action="store_true",
                    help="Actually remove redundant copies (default: report only).")
    dd.add_argument("--limit", "-n", type=int, default=None,
                    help="Only scan the N most-recent liked songs.")

    cfg = sub.add_parser("configure", help="Interactively create your user config + credentials.")
    cfg.add_argument("--prefix", default=None, help="Playlist name prefix.")
    cfg.add_argument("--public", dest="public", action="store_const", const=True, default=None,
                     help="Make created playlists public.")
    cfg.add_argument("--private", dest="public", action="store_const", const=False,
                     help="Make created playlists private.")
    cfg.add_argument("--providers", default=None, help="Comma-separated genre sources, in order.")
    cfg.add_argument("--decade-floor", type=int, default=None, help="Earliest decade year.")
    cfg.add_argument("--discogs-token", default=None, help="Discogs token (stored in credentials).")
    cfg.add_argument("--spotify-client-id", default=None)
    cfg.add_argument("--spotify-client-secret", default=None)
    cfg.add_argument("--spotify-redirect", default=None, help="Spotify redirect URI.")
    cfg.add_argument("--force", action="store_true", help="Overwrite an existing user config.")
    cfg.add_argument("--non-interactive", action="store_true",
                     help="Write from flags/defaults without prompting.")

    sub.add_parser("auth", help="Run the OAuth flow / refresh the cached token and exit.")
    return p


def cmd_sort(args) -> int:
    from .auth import get_client
    from .cache import GenreCache
    from .classify import build_classifiers
    from .config import Config
    from .library import fetch_liked_tracks
    from .providers import build_providers, resolve_genres
    from .sorter import Sorter

    config = Config.load(args.config)
    sp = get_client()
    sorter = Sorter(sp, config)

    print("Fetching Liked Songs…", flush=True)
    tracks = fetch_liked_tracks(sp, limit=args.limit)
    print(f"  {len(tracks)} tracks")

    if "genre" in args.dimensions:
        print("Resolving genres (" + " → ".join(config.genre_providers) + ")…", flush=True)
        cache = GenreCache(config.cache_path)
        resolve_genres(tracks, build_providers(config, sp, cache))
        cache.save()

    classifiers = build_classifiers(config, args.dimensions)
    plan = sorter.plan(tracks, classifiers)

    print(f"\nPlan: {plan.total_placements} placements across "
          f"{len(plan.by_playlist)} playlists "
          f"({'dry run' if args.dry_run else 'applying'}):")
    for name, ids in sorted(plan.by_playlist.items()):
        print(f"  {len(ids):>4}  {name}")
    if plan.skipped_tracks:
        print(f"  ({len(plan.skipped_tracks)} tracks matched no dimension and were skipped)")

    print()
    for line in sorter.apply(plan, dry_run=args.dry_run):
        print("  " + line)
    print("\nDone." if not args.dry_run else "\nDry run complete — nothing was changed.")
    return 0


def cmd_dedupe(args) -> int:
    from .auth import get_client
    from .config import Config
    from .dedupe import apply_removals, find_duplicates
    from .library import fetch_liked_tracks
    from .sorter import Sorter

    sp = get_client()
    print("Fetching Liked Songs…", flush=True)
    tracks = fetch_liked_tracks(sp, limit=args.limit)
    print(f"  {len(tracks)} tracks")

    groups = find_duplicates(tracks)
    exact = [g for g in groups if g.kind == "exact"]
    pairs = [g for g in groups if g.kind == "version_pair" and not g.unresolved]
    unresolved = [g for g in groups if g.unresolved]

    def show(group) -> None:
        for t in group.tracks:
            mark = "keep" if t.id == group.keep_id else ("drop" if t.id in group.remove_ids else "  · ")
            print(f"      {mark}  {t.label}")

    print(f"\nExact duplicates: {len(exact)} group(s)")
    for g in exact:
        show(g)
    print(f"\nVersion pairs — keep original: {len(pairs)} group(s)")
    for g in pairs:
        show(g)
    print(f"\nUnresolved — kept both: {len(unresolved)} group(s)")
    for g in unresolved:
        show(g)

    remove_ids = [rid for g in groups for rid in g.remove_ids]
    print(f"\n{len(remove_ids)} redundant copies identified.")
    if not remove_ids:
        return 0
    if not args.apply:
        print("Report only — re-run with --apply to remove them.")
        return 0
    sorter = Sorter(sp, Config.load())
    print()
    for line in apply_removals(sp, sorter, remove_ids, dry_run=False):
        print("  " + line)
    print("\nDone.")
    return 0


def main(argv: list[str] | None = None) -> int:
    from .credentials import load_into_env

    _load_dotenv()          # project-local .env fills unset vars first…
    load_into_env()         # …then the per-user credentials file fills what remains.
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "configure":
        from .configure import run_configure
        return run_configure(args)
    if args.command == "auth":
        from .auth import get_client
        get_client().current_user()
        print("Authenticated. Token cached in .cache")
        return 0
    if args.command == "sort":
        return cmd_sort(args)
    if args.command == "dedupe":
        return cmd_dedupe(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
