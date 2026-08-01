"""Detect and (optionally) remove duplicate Liked Songs.

The detection functions (`normalize_key`, `group`, `classify`, `choose_removals`,
`find_duplicates`) are pure and unit-testable without any network access. Only
`apply_removals` talks to Spotify.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .library import Track

# Words that, when they appear after a " - " in a title, mark a version variant.
_VERSION_KEYWORDS = (
    "remaster", "remastered", "live", "radio edit", "single version", "single",
    "edit", "extended", "remix", "deluxe", "mono", "stereo", "version", "mix",
    '12"', '7"', "original",
)
_FEAT_RE = re.compile(r"\s*[\(\[]\s*(feat|ft|with)\b[^)\]]*[\)\]]", re.IGNORECASE)
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")

# Exact-duplicate duration tolerance (same recording): 3 seconds.
DEFAULT_TOLERANCE_MS = 3000


def version_tag(title: str) -> str | None:
    """Return the trailing "- <tag>" if it looks like a version variant, else None."""
    if " - " not in title:
        return None
    tag = title.rsplit(" - ", 1)[1].strip().lower()
    if any(k in tag for k in _VERSION_KEYWORDS):
        return tag
    return None


def _strip_title(title: str) -> str:
    t = title.lower()
    t = _FEAT_RE.sub("", t)
    if " - " in t and version_tag(title):  # drop a recognised version suffix
        t = t.rsplit(" - ", 1)[0]
    return _NONALNUM_RE.sub(" ", t).strip()


def _strip_artist(artist: str) -> str:
    a = artist.lower().split(",")[0].split(" & ")[0].split(" feat")[0]
    a = _NONALNUM_RE.sub(" ", a).strip()
    return a[4:] if a.startswith("the ") else a


def normalize_key(title: str, artist: str) -> str:
    """Key that collapses the same song across versions/credits (title | primary artist)."""
    return f"{_strip_title(title)}|{_strip_artist(artist)}"


def group(tracks: list[Track]) -> list[list[Track]]:
    """Group tracks that represent the same song; only groups of 2+ are returned."""
    buckets: dict[str, list[Track]] = {}
    for t in tracks:
        buckets.setdefault(normalize_key(t.name, t.primary_artist), []).append(t)
    return [g for g in buckets.values() if len(g) > 1]


def classify(g: list[Track], tolerance_ms: int = DEFAULT_TOLERANCE_MS) -> str:
    """Return "exact" (same recording) or "version_pair" (differing versions)."""
    durs = [t.duration_ms for t in g if t.duration_ms is not None]
    spread = (max(durs) - min(durs)) if durs else 0
    tag_states = {version_tag(t.name) for t in g}
    if spread <= tolerance_ms and len(tag_states) <= 1:
        return "exact"
    return "version_pair"


def choose_removals(g: list[Track], kind: str) -> tuple[str | None, list[str], bool]:
    """Return (keep_id, remove_ids, unresolved).

    unresolved=True means the original couldn't be determined; keep everything.
    """
    if kind == "exact":
        return g[0].id, [t.id for t in g[1:]], False

    tagged = [(t, version_tag(t.name)) for t in g]
    original = [t for t, tag in tagged if tag and "original" in tag]
    untagged = [t for t, tag in tagged if tag is None]
    if original:
        keeper = original[0]           # an explicit "Original ..." mix wins
    elif len(untagged) == 1:
        keeper = untagged[0]           # the sole untagged copy is the original
    else:
        return None, [], True          # all tagged, or several untagged -> unresolved
    return keeper.id, [t.id for t in g if t.id != keeper.id], False


@dataclass
class DupGroup:
    kind: str                 # "exact" | "version_pair"
    tracks: list[Track]
    keep_id: str | None
    remove_ids: list[str]
    unresolved: bool


def find_duplicates(tracks: list[Track], tolerance_ms: int = DEFAULT_TOLERANCE_MS) -> list[DupGroup]:
    out: list[DupGroup] = []
    for g in group(tracks):
        kind = classify(g, tolerance_ms)
        keep, remove, unresolved = choose_removals(g, kind)
        out.append(DupGroup(kind, g, keep, remove, unresolved))
    return out


def apply_removals(sp, sorter, remove_ids: list[str], dry_run: bool = False) -> list[str]:
    """Un-save `remove_ids` from Liked Songs and purge them from owned playlists.

    `sorter` is a spotify_sorter.sorter.Sorter (used to enumerate owned playlists).
    Returns human-readable action lines.
    """
    actions: list[str] = []
    if not remove_ids:
        return ["nothing to remove"]
    remove_set = set(remove_ids)
    if dry_run:
        actions.append(f"[dry-run] would un-save {len(remove_ids)} tracks from Liked Songs")
    else:
        for i in range(0, len(remove_ids), 40):
            sp.current_user_saved_tracks_delete(tracks=remove_ids[i : i + 40])
        actions.append(f"un-saved {len(remove_ids)} tracks from Liked Songs")

    # Purge removed copies from every playlist the user owns.
    for name, pid in sorter._existing_playlists().items():
        present = [tid for tid in sorter._playlist_track_ids(pid) if tid in remove_set]
        if not present:
            continue
        if dry_run:
            actions.append(f"[dry-run] would remove {len(present)} from '{name}'")
            continue
        for i in range(0, len(present), 100):
            sp.playlist_remove_all_occurrences_of_items(pid, present[i : i + 100])
        actions.append(f"purged {len(present)} from '{name}'")
    return actions
