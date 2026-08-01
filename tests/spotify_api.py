"""A stateful mock of the Spotify Web API, wired through the `responses` library.

Real spotipy code runs against these canned HTTP endpoints, so tests exercise the
actual request/response parsing — not a hand-rolled stand-in. Use inside a
`@responses.activate` test: build a `MockAPI`, call `.register()`, then drive our
code with `spotipy.Spotify(auth="test-token")`.
"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

import responses

BASE = "https://api.spotify.com/v1"


def saved_track(tid, name="Song", artists=(("a1", "Artist"),), year=2000, duration_ms=200000):
    return {
        "id": tid,
        "name": name,
        "artists": [{"id": a, "name": n} for a, n in artists],
        "album": {"release_date": f"{year}-01-01"},
        "duration_ms": duration_ms,
    }


def _pat(path_regex: str) -> re.Pattern:
    # Anchored so e.g. /me doesn't match /me/tracks; tolerant of trailing slash + query.
    return re.compile("^" + re.escape(BASE) + path_regex + r"/?(\?.*)?$")


def _ids_from_uris(items) -> list[str]:
    out = []
    for it in items:
        uri = it.get("uri", "") if isinstance(it, dict) else it
        out.append(uri.rsplit(":", 1)[-1])
    return out


def _q(request):
    return parse_qs(urlparse(request.url).query)


def _path_parts(request):
    return urlparse(request.url).path.split("/")


class MockAPI:
    def __init__(self, saved=None, artist_genres=None, playlists=None, user_id="me"):
        self.user_id = user_id
        self.saved = list(saved or [])
        self.artist_genres = dict(artist_genres or {})
        self.playlists = dict(playlists or {})  # id -> {name, owner_id, tracks:[track_id]}
        self._n = 0

    # --- GET callbacks ---
    def _me(self, request):
        return 200, {}, json.dumps({"id": self.user_id})

    def _saved(self, request):
        q = _q(request)
        limit = int(q.get("limit", ["20"])[0])
        offset = int(q.get("offset", ["0"])[0])
        page = self.saved[offset : offset + limit]
        nxt = f"{BASE}/me/tracks?offset={offset + limit}" if offset + limit < len(self.saved) else None
        return 200, {}, json.dumps({"items": [{"track": t} for t in page], "next": nxt,
                                    "total": len(self.saved)})

    def _artists(self, request):
        ids = _q(request).get("ids", [""])[0]
        ids = ids.split(",") if ids else []
        return 200, {}, json.dumps(
            {"artists": [{"id": a, "genres": self.artist_genres.get(a, [])} for a in ids]}
        )

    def _playlists(self, request):
        q = _q(request)
        limit = int(q.get("limit", ["50"])[0])
        offset = int(q.get("offset", ["0"])[0])
        items = [{"name": p["name"], "id": pid, "owner": {"id": p["owner_id"]}}
                 for pid, p in self.playlists.items()]
        page = items[offset : offset + limit]
        nxt = f"{BASE}/me/playlists?offset={offset + limit}" if offset + limit < len(items) else None
        return 200, {}, json.dumps({"items": page, "next": nxt, "total": len(items)})

    def _playlist_items(self, request):
        pid = _path_parts(request)[-2]
        q = _q(request)
        limit = int(q.get("limit", ["100"])[0])
        offset = int(q.get("offset", ["0"])[0])
        tracks = self.playlists[pid]["tracks"]
        page = tracks[offset : offset + limit]
        nxt = (f"{BASE}/playlists/{pid}/tracks?offset={offset + limit}"
               if offset + limit < len(tracks) else None)
        return 200, {}, json.dumps({"items": [{"track": {"id": t}} for t in page], "next": nxt})

    # --- write callbacks ---
    def _create(self, request):
        uid = _path_parts(request)[-2]
        body = json.loads(request.body or "{}")
        self._n += 1
        pid = f"pl{self._n}"
        self.playlists[pid] = {"name": body.get("name", ""), "owner_id": uid, "tracks": []}
        return 201, {}, json.dumps({"id": pid, "name": body.get("name", ""),
                                    "owner": {"id": uid}})

    def _add(self, request):
        # spotipy POSTs a bare JSON list of track URIs to /playlists/{id}/items
        pid = _path_parts(request)[-2]
        items = json.loads(request.body or "[]")
        self.playlists[pid]["tracks"].extend(_ids_from_uris(items))
        return 201, {}, json.dumps({"snapshot_id": "snap"})

    def _remove(self, request):
        # DELETE /playlists/{id}/items with body {"items": [{"uri": ...}, ...]}
        pid = _path_parts(request)[-2]
        body = json.loads(request.body or "{}")
        gone = set(_ids_from_uris(body.get("items", [])))
        p = self.playlists[pid]
        p["tracks"] = [t for t in p["tracks"] if t not in gone]
        return 200, {}, json.dumps({"snapshot_id": "snap"})

    def _saved_delete(self, request):
        # DELETE me/library?uris=spotify:track:id1,spotify:track:id2
        uris = _q(request).get("uris", [""])[0]
        gone = {u.rsplit(":", 1)[-1] for u in uris.split(",") if u}
        self.saved = [t for t in self.saved if t.get("id") not in gone]
        return 200, {}, json.dumps({})

    def register(self):
        r = responses
        r.add_callback(r.GET, _pat("/me"), callback=self._me)
        r.add_callback(r.GET, _pat("/me/tracks"), callback=self._saved)
        r.add_callback(r.DELETE, _pat("/me/library"), callback=self._saved_delete)
        r.add_callback(r.GET, _pat("/artists"), callback=self._artists)
        r.add_callback(r.GET, _pat("/me/playlists"), callback=self._playlists)
        r.add_callback(r.GET, _pat("/playlists/[^/]+/items"), callback=self._playlist_items)
        r.add_callback(r.POST, _pat("/users/[^/]+/playlists"), callback=self._create)
        r.add_callback(r.POST, _pat("/playlists/[^/]+/items"), callback=self._add)
        r.add_callback(r.DELETE, _pat("/playlists/[^/]+/items"), callback=self._remove)
        return self
