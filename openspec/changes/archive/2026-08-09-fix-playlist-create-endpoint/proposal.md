## Why

A real `sort` run cannot create a playlist. Creation goes through an endpoint Spotify removed in
February 2026, with an explicit replacement named in the changelog. Any run that needs a bucket
which does not already exist fails at that point — after the library has been fetched and genres
resolved, so the expensive work is discarded too.

It has gone unnoticed because every live verification so far has been a dry run, and the dry-run
path returns before reaching the creation call. A full-library dry run on a 1853-track account
planned a new `1950s` playlist; that is the call that would have failed. The unit tests do not
catch it either, since the test double faithfully implements the endpoint that no longer exists.

## What Changes

- Create playlists through the current-user endpoint. The pinned client library already ships the
  replacement method, so this is a call-site swap rather than new plumbing.
- Update the test double to model the endpoint that exists, so the suite stops validating against
  a removed one.
- State in the spec that a created playlist is owned by the authenticated user. This is not a
  behavior change; it makes explicit something idempotency already depends on.
- **Not changed**: what gets created, its name, its visibility, when creation happens, or the
  matching and de-duplication around it.

## Capabilities

### New Capabilities
<!-- None. This fixes an existing capability. -->

### Modified Capabilities
- `sorting`: the idempotent-apply requirement gains a statement that a newly created playlist is
  owned by the authenticated user. Every other part of that requirement is unchanged.

## Why the ownership clause belongs in the spec, and the endpoint does not

Which endpoint performs the creation is wire-level detail. The spec describes what a user
observes — a playlist appears, with the configured visibility — and that is unchanged here. An
implementation reading current platform documentation will use whatever endpoint currently
exists, so pinning one buys nothing and dates the spec.

Ownership is different, and it is load-bearing. Two requirements depend on each other: the apply
requirement matches target playlists by name and creates only when no match exists, while a
separate requirement restricts matching to playlists the authenticated user owns. For a re-run to
match what a previous run created, the created playlist must be owned by that same user. Nothing
currently says so. An implementation that created a playlist owned by anyone else would fail to
match it next time and create a duplicate — on every run, indefinitely — and no single requirement
read on its own would reveal the flaw.

## Impact

- **Code**: one call site in the apply path. The user-id helper stays, since ownership filtering
  during matching still needs it.
- **Tests**: the double must move to the current endpoint. Worth noting it currently discards the
  visibility flag, so the "created with the configured visibility" scenario has never actually
  been asserted — only read from the source.
- **Runtime**: none. Same request count, same result.
- **Not fixed here**: the other February 2026 removal affecting this project (the batch artists
  endpoint, which breaks the always-available genre source) and the behavior that turns any source
  error into an aborted run.
