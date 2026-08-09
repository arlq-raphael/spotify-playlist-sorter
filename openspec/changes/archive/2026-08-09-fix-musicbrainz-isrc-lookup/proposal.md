## Why

The ISRC genre source has never worked against the live API. It asks the ISRC resource for
genres, which that resource does not accept:

```
{"error":"genres is not a valid inc parameter for the isrc resource."}  HTTP 400
```

The error is about the parameter, not the value, so every ISRC fails. Because this source is
first in the default provider order, and because an error from a source aborts the whole run
(#18), `sort` crashes for anyone on a default config as soon as a liked track carries an ISRC —
which is nearly every track.

The unit tests did not catch it: they mock the HTTP layer with a fixture that includes a
`genres` key on the ISRC response, a shape the real endpoint never returns. Response parsing was
verified; the request never was.

## What Changes

- Resolve the ISRC to a recording first, then read that recording's genres. Genres are an
  attribute of a recording, not of the ISRC index, so obtaining them takes two lookups.
- When an ISRC maps to more than one recording, use the first. This is a deliberate narrowing —
  see below.
- Model both real endpoints in the test double, including rejecting the invalid request the way
  the live API does, so this class of bug fails a test rather than reaching a user.
- **Not changed**: the fallthrough behavior when the lookup yields nothing, the caching of
  results (including empty ones), the 1 req/sec pacing, or the provider's position in the order.

## Capabilities

### New Capabilities
<!-- None. This fixes an existing capability. -->

### Modified Capabilities
- `genre-providers`: the ISRC-first requirement gains a rule for how an ISRC that identifies
  more than one recording resolves. Everything else about that requirement is unchanged.

## Why the multi-recording rule belongs in the spec, and the request shape does not

The invalid request is wire-level detail and self-correcting: a reimplementation that tries the
one-step call receives an error naming the exact problem. Pinning endpoint shapes into a spec
that is otherwise implementation-neutral would buy nothing.

The multi-recording rule is different. An ISRC can identify several recordings, and the previous
code combined genres from all of them. Taking the first is a real behavior narrowing, and no API
error would ever reveal a different choice — a reimplementation could reasonably combine all of
them, making more requests and returning different genres, and nothing would flag the divergence.
That is precisely the kind of decision a spec exists to hold.

## Impact

- **Code**: `musicbrainz.py` — the client's request flow. No change to the provider, the cache,
  or the ordering logic.
- **Tests**: the MusicBrainz test double must model both endpoints and reject the invalid
  request, so the fixture stops being more permissive than the real service.
- **Runtime**: a cold-cache run pays two requests per track with an ISRC instead of one, so at
  1 req/sec the ISRC stage takes roughly twice as long. Results are cached, including empty ones,
  so this is a first-run cost. A large library feels it: at ~1850 tracks, that stage moves from
  roughly half an hour to roughly an hour on a cold cache.
- **Not fixed here**: #18. A source that errors still aborts the run. This change removes the
  error that is firing today, but not the fragility that turns any future error into a crash.
