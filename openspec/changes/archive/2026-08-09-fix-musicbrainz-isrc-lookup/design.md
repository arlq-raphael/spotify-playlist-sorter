## Context

See proposal.md — Why. The shaping constraint is the source's 1 req/sec policy: correctness here
is cheap, but every extra request per track is paid linearly across the library, and the library
is the thing that is large.

## Goals / Non-Goals

**Goals:**
- Make the ISRC source actually return genres.
- Keep the per-track cost bounded and predictable.
- Make the test double reject what the real service rejects, so the next wrong request fails a
  test instead of a user.

**Non-Goals:**
- Fixing the crash-on-error behavior (#18). This removes the error firing today, not the
  fragility that turns any error into an aborted run.
- Changing provider order, caching, or the fallthrough contract.
- Broadening the source to use tags. Tags are a folksonomy of which genres are a curated subset;
  substituting them would quietly change what this source means by "genre".

## Decisions

**Two lookups, not one.** Genres are an attribute of a recording; the ISRC index does not carry
them and rejects the request outright. There is no single-request route to genres by ISRC — a
recording browse by ISRC is also rejected. *Alternative considered:* switch to `tags`, available
in one request on the ISRC resource. Rejected: it changes the meaning of the result, and the
whole reason this source runs first is that it is the exact, curated one. Trading that for
folksonomy data to save a request undercuts its place in the order.

**Follow only the first recording.** An ISRC can identify several recordings; the previous code
combined genres across all of them, which under a two-lookup design would mean one lookup per
recording and an unbounded per-track cost. Taking the first keeps it at two, and matches the
spec's own singular framing ("that recording"). The cost is real but small: multi-recording ISRCs
are uncommon, and the additional recordings are usually near-duplicates. *Alternative considered:*
follow up to N recordings and merge. Rejected as complexity for a case that rarely arises, with a
silent cap to explain.

**Throttle every request, not every track.** The pacing policy applies per request. The previous
code throttled once per track because there was one request; with two, both must be paced or the
source is queried at twice the permitted rate. This is easy to get wrong by leaving the throttle
where it was, and nothing in a passing test suite would reveal it.

**Make the test double reject the invalid request.** The reason this shipped is that the fixture
was more permissive than the service: it returned genres on a response shape that never carries
them. Modelling both endpoints is necessary but not sufficient — the double should also answer
the invalid request the way the live API does. Then reintroducing the original bug turns a test
red rather than passing quietly.

## Risks / Trade-offs

- **Cold-cache runs roughly double in the ISRC stage.** → Accepted, and stated in the proposal.
  Results are cached including empty ones, so it is a first-run cost. If it proves painful, the
  answer is a shipped cache seed or relaxing the source order, not a semantic downgrade to tags.
- **Follow-the-first can pick a recording with no genres when a sibling has some.** → Accepted.
  The track falls through to the next source, which is the designed behavior for an unresolved
  lookup, so the outcome is a fallthrough rather than a wrong answer.
- **Expected yield is modest.** Probing a real track showed the identified recording carrying
  neither genres nor tags. Many tracks will resolve to nothing and fall through. This change
  should be judged on removing the crash and returning correct data when it exists, not on how
  many extra tracks get classified.

## Migration Plan

None. No config, no data, no user-visible interface change. Existing cache entries stay valid:
they are keyed by ISRC and hold final genre lists, which this does not change the shape of.
