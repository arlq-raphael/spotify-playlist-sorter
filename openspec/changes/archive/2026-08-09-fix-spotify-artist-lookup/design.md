## Context

See proposal.md — Why. The shaping fact is a 49× change in request volume: 27 batched calls
become 1333 individual ones. That is cheap in wall-clock terms (measured at ~2.4 minutes) but it
changes the arithmetic of failure, which is the part worth deciding before writing code rather
than discovering during it.

## Goals / Non-Goals

**Goals:**
- Restore the source using the endpoint that still exists.
- Keep the per-run and across-run cost proportionate to distinct artists, not to track references.
- Decide, rather than inherit, what one failing lookup does now that there are 1333 of them.

**Non-Goals:**
- Reordering the provider chain. The measurements make that question obvious and it is argued in
  the proposal, but answering it here would smuggle a behavioral trade into a bug fix.
- Fixing the run-aborting behavior of a failing source (#18). This change should not make that
  path more likely to fire; repairing it is separate.
- Changing what genres a given artist yields.

## Decisions

**Look artists up individually, rather than dropping the source.** The alternative considered was
removing Spotify from the chain entirely, on the theory that per-artist lookups would be
prohibitive. Measurement says otherwise — 0.11s each, ~2.4 minutes for the whole library, no rate
limiting at that volume — while dropping the source would strand roughly 964 tracks, over half the
library, since the exact ISRC source resolves only 48%. Two and a half minutes is not a reason to
lose half the coverage.

**Cache by artist, namespaced.** The cache is shared across sources and already holds recording
keys and artist+title keys. Artist keys need their own prefix so they cannot collide — a bare
artist id could in principle coincide with another source's key, and a collision would silently
serve the wrong genres. Empty results are cached like every other source's, so an artist with no
genres costs one lookup ever rather than one per run. Without this, every run pays the full 1333;
with it, only the first does.

**A failing artist lookup skips that artist and the run continues.** This is the decision that was
nearly deferred into implementation. Three reasons to settle it here:

- The design intent throughout is that genre sources are best-effort. A missing Discogs token
  skips that source with a notice rather than failing; a track that resolves to nothing falls
  through. One unreachable artist should behave the same way.
- The exposure grew 49×. Under batching, a transient error was one failure in 27; now it is one in
  1333, so inheriting "any error kills the run" would make #18 far more likely to fire as a direct
  consequence of this change.
- A track usually credits more than one artist, so skipping one often costs nothing at all — the
  track still receives the others' genres.

*Alternative considered:* let it propagate, on the grounds that #18 is the proper place to fix
error handling. Rejected because it would knowingly multiply the blast radius of a known bug by 49
while claiming to be a fix.

**Failures are reported, not swallowed.** A source that silently returns nothing is
indistinguishable from a source that legitimately has nothing, which is the trap #18 describes.
One summary notice when any artist lookup failed is enough — per-artist noise across 1333 lookups
would be worse than useless.

## Risks / Trade-offs

- **1333 sequential requests is slow if Spotify throttles harder than observed.** → Measured on 20
  requests, which is a small sample; task 5.5 measures the real cold run before this is claimed as
  settled. The cache means the cost is paid once, so even a worse-than-expected first run degrades
  to a one-time delay rather than a recurring one.
- **Skipping a failing artist can silently reduce a track's genres** rather than failing loudly. →
  Accepted, and the reason failures are reported. It matches how every other source in the chain
  already behaves.
- **The cache grows by one entry per distinct artist.** → 1333 entries of a few genre strings.
  Negligible next to the existing per-track entries.

## Migration Plan

None. Existing cache entries stay valid: artist keys are new and namespaced, so nothing already
stored is read differently. A first run after this lands re-fetches artists once and caches them.
