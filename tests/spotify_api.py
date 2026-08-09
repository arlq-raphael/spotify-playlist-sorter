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
    def __init__(self, saved=None, artist_genres=None, playlists=None, user_id="me",
                 artist_errors=None):
        self.user_id = user_id
        self.saved = list(saved or [])
        self.artist_genres = dict(artist_genres or {})
        self.playlists = dict(playlists or {})  # id -> {name, owner_id, tracks:[track_id]}
        # {artist_id: status} — lets a test make one lookup fail among many, which is the
        # case that matters now that artists are fetched one at a time (#23).
        self.artist_errors = dict(artist_errors or {})
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

    def _artists_batch(self, request):
        # GET /artists?ids=... was removed from the Web API in Feb 2026 and now answers with a
        # bare 403. Serving it here is what let a dead code path keep looking healthy (#23).
        return 403, {}, json.dumps({"error": {"status": 403, "message": "Forbidden"}})

    def _artist(self, request):
        aid = _path_parts(request)[-1]
        if aid in self.artist_errors:
            return self.artist_errors[aid], {}, json.dumps({"error": {"status": 500}})
        return 200, {}, json.dumps({"id": aid, "genres": self.artist_genres.get(aid, [])})

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
        nxt = (f"{BASE}/playlists/{pid}/items?offset={offset + limit}"
               if offset + limit < len(tracks) else None)
        # Entries nest under "item", not "track" — renamed alongside the Feb 2026 move from
        # /playlists/{id}/tracks to /playlists/{id}/items. Returning the old shape here is
        # what let a silent idempotency break ship (#25).
        #
        # `fields` is honored, not ignored: a projection naming a key that does not exist
        # yields empty entries, exactly as the live API does. Ignoring it would let a wrong
        # projection pass every test while returning nothing in production — which is how
        # the same bug survived its own regression test.
        fields = q.get("fields", [None])[0]
        entries = [{"item": {"id": t}} for t in page]
        if fields and "item(" not in fields:
            entries = [{} for _ in page]
        return 200, {}, json.dumps({"items": entries, "next": nxt})

    # --- write callbacks ---
    def _create(self, request):
        # POST /me/playlists — the per-user form was removed from the Web API in Feb 2026.
        # The owner comes from the mock's own user, not the URL: a created playlist belongs
        # to the authenticated user regardless of the endpoint's shape.
        body = json.loads(request.body or "{}")
        self._n += 1
        pid = f"pl{self._n}"
        self.playlists[pid] = {
            "name": body.get("name", ""),
            "owner_id": self.user_id,
            "public": body.get("public"),   # recorded so visibility can be asserted
            "tracks": [],
        }
        return 201, {}, json.dumps({"id": pid, "name": body.get("name", ""),
                                    "public": body.get("public"),
                                    "owner": {"id": self.user_id}})

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
        # Order matters: the batch pattern must be registered before the single-artist one,
        # so `/artists?ids=...` is answered as removed rather than matching `/artists/{id}`.
        r.add_callback(r.GET, _pat("/artists"), callback=self._artists_batch)
        r.add_callback(r.GET, _pat("/artists/[^/]+"), callback=self._artist)
        r.add_callback(r.GET, _pat("/me/playlists"), callback=self._playlists)
        r.add_callback(r.GET, _pat("/playlists/[^/]+/items"), callback=self._playlist_items)
        r.add_callback(r.POST, _pat("/me/playlists"), callback=self._create)
        r.add_callback(r.POST, _pat("/playlists/[^/]+/items"), callback=self._add)
        r.add_callback(r.DELETE, _pat("/playlists/[^/]+/items"), callback=self._remove)
        return self


def mock_musicbrainz(isrc_genres: dict):
    """Register the two MusicBrainz endpoints an ISRC genre lookup needs, as the live
    service actually behaves.

    `isrc_genres` maps an ISRC to the genres of the recording(s) it identifies:

        {"ISRC1": ["techno"]}                 one recording carrying those genres
        {"ISRC1": [["techno"], ["dub"]]}      several recordings, in order

    A missing ISRC returns 404. Genres live on the RECORDING, never on the ISRC
    response — asking the ISRC resource for them is rejected here exactly as the live
    API rejects it, which is the whole point: a fixture that answered that request is
    why an invalid one shipped (see #17).
    """
    def recordings_for(isrc):
        val = isrc_genres.get(isrc)
        if val is None:
            return None
        groups = val if val and isinstance(val[0], list) else [val]
        return [(f"mbid-{isrc}-{i}", g) for i, g in enumerate(groups)]

    genres_by_mbid = {
        mbid: g for isrc in isrc_genres for mbid, g in (recordings_for(isrc) or [])
    }

    def isrc_cb(request):
        query = parse_qs(urlparse(request.url).query)
        inc = query.get("inc", [""])[0]
        if "genres" in inc:
            # The live service refuses this outright; so must the double.
            return 400, {}, json.dumps({
                "help": "For usage, please see: https://musicbrainz.org/development/mmd",
                "error": "genres is not a valid inc parameter for the isrc resource.",
            })
        isrc = urlparse(request.url).path.rstrip("/").split("/")[-1]
        found = recordings_for(isrc)
        if found is None:
            return 404, {}, json.dumps({"error": "Not Found"})
        # Note the absence of any genre data — matching the real response.
        recordings = [{"id": mbid, "title": "t", "length": 1000} for mbid, _ in found]
        return 200, {}, json.dumps({"isrc": isrc, "recordings": recordings})

    def recording_cb(request):
        mbid = urlparse(request.url).path.rstrip("/").split("/")[-1]
        if mbid not in genres_by_mbid:
            return 404, {}, json.dumps({"error": "Not Found"})
        body = {"id": mbid, "title": "t"}
        if "genres" in parse_qs(urlparse(request.url).query).get("inc", [""])[0]:
            body["genres"] = [{"name": g, "count": 1} for g in genres_by_mbid[mbid]]
        return 200, {}, json.dumps(body)

    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/isrc/[^/?]+"), callback=isrc_cb
    )
    responses.add_callback(
        responses.GET, re.compile(r"^https://musicbrainz\.org/ws/2/recording/[^/?]+"),
        callback=recording_cb,
    )


def mock_discogs(search_results: dict):
    """Register the Discogs search endpoint. `search_results`: {"artist|title":
    {"genre": [...], "style": [...]}}; a missing key returns no results."""
    def norm(s):
        return " ".join(s.lower().split())

    def cb(request):
        q = parse_qs(urlparse(request.url).query)
        key = f"{norm(q.get('artist', [''])[0])}|{norm(q.get('track', [''])[0])}"
        hit = search_results.get(key)
        results = []
        if hit:
            results = [{"id": 1, "type": "release", "title": "X",
                        "resource_url": "https://api.discogs.com/releases/1",
                        "genre": hit.get("genre", []), "style": hit.get("style", [])}]
        return 200, {}, json.dumps(
            {"results": results,
             "pagination": {"items": len(results), "page": 1, "pages": 1, "per_page": 50}}
        )

    responses.add_callback(
        responses.GET, re.compile(r"^https://api\.discogs\.com/database/search"), callback=cb
    )
