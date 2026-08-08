## Context

See proposal.md — Why. The constraint that shapes everything here is that this spec has two
audiences: the current implementation, which it must describe accurately today, and a possible
future implementation in another language (#8), which it must be able to govern without being
rewritten. A spec that leaks the current implementation's vocabulary would satisfy the first
audience and fail the second.

The other five specs in `openspec/specs/` set the precedent: a search for implementation
coupling across them returns six hits, all in `config-loading` (packaging vocabulary) or in
credential key names that are user-facing contract. `sorting` should land at zero.

## Goals / Non-Goals

**Goals:**
- Describe the existing sort behavior accurately enough that a fresh implementation passing
  every scenario would be accepted as a faithful replacement.
- Keep the spec implementation-neutral: no module, function, type, library, or language names.
- Verify each scenario against the running implementation while writing it.

**Non-Goals:**
- Changing any behavior, including behavior that looks questionable while being documented.
- Specifying genre *resolution* (owned by `genre-providers`), config layering (owned by
  `config-loading`), or duplicate handling (owned by `dedupe`).
- Adding tests. The existing suite is the verification instrument here, not a deliverable.

## Decisions

**Document behavior as-is; file defects separately.**
A backfill that "fixes while documenting" produces a spec matching neither the old nor the new
behavior, and silently changes a shipped tool. Anything that looks wrong gets an issue, and the
spec records what the code does today. *Alternative considered:* correct small oddities inline —
rejected because it makes the spec unverifiable against the current suite, which is the only
evidence available that the description is right.

This decision was exercised immediately: the decade floor does not route pre-floor tracks to a
catch-all, it rewrites the year, so a 1935 track lands in a playlist named `1950s` (#10). That
is documented here as-is, with a scenario stating the relabeling explicitly so a reimplementation
cannot reproduce it by accident; the fix is proposed separately in #10.

**Verify against the existing test suite rather than adding tests.**
Nearly every scenario in the spec already has a corresponding assertion — first-match-wins
ordering, substring matching, both genre fallbacks, the decade floor clamp, the skip path,
create-then-idempotent apply, dry-run non-mutation, owner filtering, and pagination past one
page of playlists and one page of playlist items. Writing the spec is therefore mostly a matter
of reading those tests and the code they exercise, then restating the guarantees neutrally.
*Alternative considered:* write new characterization tests first — rejected as redundant, and it
would put code changes in a documentation PR.

**Express provider limits as size-independence, not as page sizes.**
The implementation pages and batches in fixed block sizes dictated by the Spotify Web API. Those
numbers are the provider's constraints, not this tool's contract, and a reimplementation using a
different client may batch differently while remaining correct. The spec states the observable
guarantee — the run completes correctly regardless of library size, existing playlist size, or
number of tracks to add — and leaves the mechanism out. *Alternative considered:* pin the exact
page sizes — rejected as over-specification a conforming implementation would violate.

**Split ownership matching into its own requirement.**
The rule that only playlists owned by the authenticated user may be matched is easy to miss when
reimplementing, and getting it wrong means writing into a playlist the user merely follows — the
one genuinely destructive failure mode in this capability. It is stated as its own requirement
rather than a clause inside the apply requirement so it cannot be skimmed past.

**Treat the disabled-dimension and unknown-dimension errors as one behavior.**
Configuration can disable a dimension, and the resulting failure is indistinguishable to the user
from requesting a dimension that never existed. The spec documents them as the same observable
outcome rather than inventing a distinction the implementation does not make.

## Risks / Trade-offs

- **The spec could encode a current bug as a requirement.** → Every scenario is checked against
  both the code and its test; anything that looks like a defect is filed rather than quietly
  specified, and the PR description lists what was deliberately documented as-is. #10 is the
  first instance.
- **Neutral phrasing can drift into vagueness.** → Each scenario must remain a testable
  WHEN/THEN. If a sentence cannot be turned into an assertion, it is too vague and gets
  rewritten.
- **`openspec/config.yaml`'s `context:` block is entirely implementation-specific** and is
  injected into every artifact generated in this repo, biasing generated text toward the current
  stack. → Out of scope to fix here; flagged in tasks so #8 rewrites it before generating port
  artifacts.

## Migration Plan

Not applicable — no code, no data, and no user-visible behavior changes. On archive, the delta
becomes `openspec/specs/sorting/spec.md` alongside the existing five capability specs.
