"""Orchestration: plan target playlists for each track, then apply changes.

Idempotent: playlists are matched by name (created if missing), and tracks
already present in a target playlist are skipped, so re-running only adds the
delta.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import spotipy

from .classify import Classifier
from .config import Config
from .library import Track


@dataclass
class Plan:
    # playlist name -> ordered, de-duplicated list of track ids
    by_playlist: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    skipped_tracks: list[tuple[Track, str]] = field(default_factory=list)  # (track, reason)

    def add(self, playlist: str, track_id: str) -> None:
        bucket = self.by_playlist[playlist]
        if track_id not in bucket:
            bucket.append(track_id)

    @property
    def total_placements(self) -> int:
        return sum(len(v) for v in self.by_playlist.values())


class Sorter:
    def __init__(self, sp: spotipy.Spotify, config: Config):
        self.sp = sp
        self.config = config
        self._user_id: str | None = None

    def user_id(self) -> str:
        if self._user_id is None:
            self._user_id = self.sp.current_user()["id"]
        return self._user_id

    # ---- planning -------------------------------------------------------
    def plan(self, tracks: list[Track], classifiers: list[Classifier]) -> Plan:
        plan = Plan()
        prefix = self.config.playlist_prefix
        for t in tracks:
            placed = False
            for clf in classifiers:
                name = clf.bucket(t)
                if name:
                    plan.add(prefix + name, t.id)
                    placed = True
            if not placed:
                plan.skipped_tracks.append((t, "no dimension produced a bucket"))
        return plan

    # ---- applying -------------------------------------------------------
    def _existing_playlists(self) -> dict[str, str]:
        """Map of playlist name -> id for playlists the user owns."""
        out: dict[str, str] = {}
        offset = 0
        uid = self.user_id()
        while True:
            res = self.sp.current_user_playlists(limit=50, offset=offset)
            for pl in res.get("items", []):
                owner = (pl.get("owner") or {}).get("id")
                if owner == uid and pl.get("name") not in out:
                    out[pl["name"]] = pl["id"]
            if not res.get("next"):
                break
            offset += 50
        return out

    def _playlist_track_ids(self, playlist_id: str) -> set[str]:
        ids: set[str] = set()
        offset = 0
        while True:
            res = self.sp.playlist_items(
                playlist_id, fields="items(track(id)),next", limit=100, offset=offset,
                additional_types=("track",),
            )
            for it in res.get("items", []):
                tr = it.get("track") or {}
                if tr.get("id"):
                    ids.add(tr["id"])
            if not res.get("next"):
                break
            offset += 100
        return ids

    def apply(self, plan: Plan, dry_run: bool = False) -> list[str]:
        """Create playlists as needed and add only the missing tracks.

        Returns a list of human-readable action lines.
        """
        actions: list[str] = []
        existing = self._existing_playlists()
        for name, track_ids in sorted(plan.by_playlist.items()):
            pid = existing.get(name)
            if pid is None:
                if dry_run:
                    actions.append(f"[dry-run] CREATE playlist '{name}'  (+{len(track_ids)} tracks)")
                    continue
                pl = self.sp.user_playlist_create(
                    self.user_id(), name, public=self.config.public_playlists
                )
                pid = pl["id"]
                existing[name] = pid
                current: set[str] = set()
                actions.append(f"CREATE playlist '{name}'")
            else:
                current = self._playlist_track_ids(pid)

            to_add = [tid for tid in track_ids if tid not in current]
            if not to_add:
                actions.append(f"'{name}': up to date ({len(track_ids)} tracks)")
                continue
            if dry_run:
                actions.append(f"[dry-run] ADD {len(to_add)} tracks to '{name}'")
                continue
            for i in range(0, len(to_add), 100):
                self.sp.playlist_add_items(pid, to_add[i : i + 100])
            actions.append(f"'{name}': added {len(to_add)} tracks")
        return actions
