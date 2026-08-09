## 1. Make the test double match the real service

Done first deliberately: the old fixture was more permissive than the live API, which is the only
reason the bug shipped. Tightening it before touching the client made the existing tests go red,
proving the double now catches what it previously waved through.

- [x] 1.1 ISRC endpoint models the real response — recordings carrying an id, and no genre data
- [x] 1.2 Recording endpoint added, returning genres for a given recording id
- [x] 1.3 The double now rejects an ISRC request asking for genres, with the live service's own
      status and message
- [x] 1.4 Confirmed: 5 of 6 existing tests went red, failing with exactly the production error —
      `400 Client Error: Bad Request for url: .../isrc/ISRC1?inc=genres%2Btags&fmt=json`

## 2. Fix the client

- [x] 2.1 ISRC resolves to a recording id, then genres are read from that recording
- [x] 2.2 First recording only when an ISRC identifies several; no merging across them
- [x] 2.3 Pacing moved into `_request`, so both lookups are paced — leaving it per-track would
      have queried the source at twice the permitted rate with nothing to reveal it
- [x] 2.4 Preserved: not-found yields no genres, busy is retried once, names lower-cased and
      de-duplicated in order

## 3. Cover the behavior the spec now pins

- [x] 3.1 One recording → its genres (`test_client_genres_for_isrc`)
- [x] 3.2 Several recordings → first only, and exactly one recording lookup is made
- [x] 3.3 Recording with no genres → empty result, still cached (second pass makes no requests)
- [x] 3.4 Not-found at either step → no genres, no raise; an ISRC with no usable recording skips
      the second lookup entirely
- [x] 3.5 Busy retried once at *either* step — two tests, since the retry has to cover both
- [x] 3.6 Both requests paced, asserted by counting throttle calls per lookup

## 4. Verify

- [x] 4.1 106 passed (was 100), coverage 98.74% — above the 97% floor
- [x] 4.2 `ruff check src tests` clean
- [x] 4.3 `openspec validate fix-musicbrainz-isrc-lookup --strict` passes
- [x] 4.4 **Verified live.** `sort --dry-run --limit 5 -d genre` against a real account passed
      through the MusicBrainz stage with no error — the 400 that motivated this change is gone.
      The run then failed further along, in the Spotify source, for an unrelated reason: see 5.3

## 5. Follow-ups

- [x] 5.1 #18 untouched and still accurate: a source that errors still aborts the run. The live
      run in 4.4 demonstrates it — an error in the *third* source discarded the work already done
      by the first two
- [x] 5.2 Cold-cache cost measured, replacing the estimate in design.md: 5 tracks took 12.5s
      end to end, so roughly 2.5s per track with an ISRC. Extrapolated to this library's 1853
      tracks that is about 75 minutes for a first run, against roughly half that before. Cached
      thereafter, including empty results
- [x] 5.3 **Found while verifying: Spotify removed the batch artists endpoint in February 2026.**
      `library.py:78` calls it for artist genres and now gets a bare 403. Separately,
      `sorter.py:108` creates playlists through an endpoint removed in the same release. Neither
      is caused by this change, both are filed separately, and the second means a real (non-dry)
      run cannot create a bucket playlist
