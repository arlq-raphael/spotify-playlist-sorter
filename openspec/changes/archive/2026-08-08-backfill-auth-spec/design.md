## Context

See proposal.md — Why. The distinguishing constraint here, compared with the `sorting` backfill,
is that most of this capability's behavior is not written in this repo. Credential resolution,
browser flow, token persistence, scope revalidation, and rate-limit retry all come from the
client library; `auth.py` supplies three environment-variable names, a scope string, and four
constructor arguments.

That makes the spec more valuable than the module's size suggests, and it changes what
verification means: several scenarios must be checked against the library's behavior rather than
against this repo's code.

## Goals / Non-Goals

**Goals:**
- Capture the authorization contract a reimplementation must satisfy, especially the parts
  currently obtained for free.
- Keep the spec implementation-neutral — no library, language, or module names.
- Shape token persistence as one requirement so #7 is a single `MODIFIED` diff.

**Non-Goals:**
- Specifying how secrets are resolved (`credentials`) or how config is layered (`config-loading`).
- Specifying Discogs or ISRC-source credentials — see the naming decision below.
- Changing behavior, including the working-directory token location that #7 will move.

## Decisions

**Name the capability `spotify-auth`, not `auth`.**
The tool authenticates to three services, and only Spotify uses an interactive flow. Discogs uses
a static token whose storage is specified by `credentials` and whose absence-handling and rate
limits are specified by `genre-providers`; the ISRC source needs no credential. A capability
named `auth` would imply it owns all three and send a reader looking for Discogs credential
handling to the wrong file. The Purpose names the specs that own the other two so the boundary is
navigable rather than merely correct. *Alternative considered:* one `auth` capability covering
every service — rejected because it would duplicate requirements already owned elsewhere, and
duplicated requirements drift.

**Specify behavior the current implementation gets for free.**
Rate-limit retry and scope revalidation are library defaults this repo never states. It is
tempting to treat them as implementation detail and leave them out. That would be a mistake: both
are observable contract, both are absent by default in the ecosystem #8 targets, and both fail
invisibly. A port without rate-limit handling passes every test and then fails on a large
library; a port without scope revalidation reuses an under-scoped authorization and surfaces a
service-side permission error that looks like a Spotify problem. Anything a reimplementation must
reproduce belongs in the spec regardless of who implements it today.

**State the retry bound without naming the numbers.**
The requirement says retries are bounded and that the service's requested delay is honored, not
that there are five of them with a 0.5 backoff factor. The specific values are a tuning choice
this repo happens to make; the contract is that a transient limit does not fail the run and a
persistent failure does not retry forever. *Alternative considered:* pin the exact retry count —
rejected as over-specification a conforming implementation would violate for good reasons.

**Document the working-directory token location as-is, and isolate it.**
The authorization is retained in the directory the command runs from, which is what #7 exists to
change. Following the discipline established in the `sorting` backfill, the current behavior is
documented rather than pre-emptively corrected — including the scenario where running from
another directory forces re-consent, which reads like a defect because it is the one #7 fixes.
Confining all of it to a single requirement means #7 replaces that requirement and touches
nothing else.

**Describe permissions by what they allow, not by their wire names.**
The spec says "permits un-saving tracks from the saved library" rather than naming the scope
string. The names are the service's vocabulary and would be identical in any implementation, but
describing the capability makes the *why* checkable — particularly that library modification is
requested for every command even though only duplicate removal uses it, because consent is
obtained once and shared.

## Risks / Trade-offs

- **The spec pins behavior owned by a dependency, which could change on upgrade.** → That is an
  argument for writing it down, not against: an upgrade that silently drops scope revalidation is
  exactly the regression this spec makes visible. The scenarios are phrased as outcomes, so they
  stay valid across library versions.
- **The re-consent-per-directory scenario reads as specifying a bug.** → It is the behavior
  today, and #7 is filed to change it. Documenting it keeps the spec honest and gives #7 a
  precise thing to modify.
- **Some scenarios cannot be verified without completing a real OAuth flow** — browser opening,
  refresh-on-expiry, live rate limiting. → Verified at the highest fidelity available short of a
  live account (library source, constructor state, existing tests) and recorded in tasks.md as
  such, rather than claimed as observed.

## Migration Plan

Not applicable — no code, no data, no user-visible behavior change. On archive the delta becomes
`openspec/specs/spotify-auth/spec.md` alongside the existing six capability specs.
