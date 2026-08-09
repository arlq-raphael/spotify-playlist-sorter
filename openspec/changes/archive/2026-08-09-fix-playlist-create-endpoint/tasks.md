## 1. Make the test double match the platform

Same ordering as the MusicBrainz fix: tighten the double first, so the existing tests go red
against the endpoint that no longer exists before any source change.

- [x] 1.1 Creation moved to the current-user endpoint in the double
- [x] 1.2 Owner derived from the double's own configured user rather than the request path, so it
      no longer depends on the URL shape
- [x] 1.3 Visibility flag recorded — the double previously discarded it, which is why "created
      with the configured visibility" had never actually been asserted
- [x] 1.4 Confirmed: 2 tests went red, failing because the endpoint moved. spotipy had also been
      emitting a `DeprecationWarning` naming the replacement on every run, unnoticed

## 2. Fix the call site

- [x] 2.1 Creates through the current-user endpoint
- [x] 2.2 User-id helper kept — matching still filters existing playlists by owner
- [x] 2.3 Visibility from configuration still passed through. **Whether the platform honors it is
      now in doubt** — see 5.3

## 3. Cover what the spec now pins

- [x] 3.1 A created playlist is owned by the authenticated user
- [x] 3.2 A playlist created by one run is matched by the next, not duplicated
- [x] 3.3 Visibility from configuration reaches the created playlist, asserted rather than read
      from the source

## 4. Verify

- [x] 4.1 109 passed (was 106), coverage 98.74%
- [x] 4.2 `ruff check src tests` clean
- [x] 4.3 `openspec validate fix-playlist-create-endpoint --strict` passes
- [x] 4.4 **Verified live.** Two throwaway playlists created through the CLI against a real
      account with an isolated prefixed config. Creation works; #22 is genuinely fixed

## 5. What the live verification exposed

The live check did what the suite could not, three times over.

- [x] 5.1 **Idempotency was broken (#25), and is fixed here.** A second run re-added every track:
      playlist entries nest under `item` since Feb 2026, and `sorter.py` read `track`. Confirmed
      by the fixtures accumulating 2 and 8 entries for 1 and 4 tracks. Not separable from #22 —
      shipping creation alone would turn a loud failure into silent duplication of 1853
      placements per run
- [x] 5.2 **The first attempt at that fix did not work, and only the live run revealed it.**
      Correcting the parser was insufficient: the request also projected
      `fields="items(track(id))"`, so the server returned empty entries regardless. Both now
      request and accept either shape, so the pair survives a revert in either direction. The
      double now honors `fields` as well — a projection naming a missing key yields empty
      entries, as the live API does. Verified the guard bites: reverting the projection turns 3
      tests red
- [x] 5.3 **Visibility is in doubt (#26).** Config asked for private; both the listing and a
      direct fetch report the playlists as public, though the flag is demonstrably sent and the
      required scope is held. Filed rather than guessed — distinguishing "ignored" from
      "misreported" needs the Spotify client UI or a second account, which the API cannot answer
- [x] 5.4 Companion Feb 2026 issue (batch artists, #23) is unaffected by this change

## 6. Cleanup

- [x] 6.1 The two `zz-verify` fixture playlists have been removed by hand; confirmed gone from the
      library via the API. Note this happened before #26 was settled, so that issue no longer has
      a fixture to inspect — reopening it means creating a fresh playlist to look at
