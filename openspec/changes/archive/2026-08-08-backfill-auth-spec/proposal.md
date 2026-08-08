## Why

Spotify authorization is the last major capability with no spec. After the `sorting` backfill,
`openspec/specs/` covers six capabilities; none of them mentions OAuth, scopes, or tokens.

`auth.py` is 37 lines, which makes it easy to assume there is nothing to write down. The
opposite is true: most of its contract is currently held by a third-party library's defaults
rather than by anything this repo states. That is exactly the contract a reimplementation loses
silently — the behavior still appears to work until it doesn't.

Two consumers need this now. The Go port (#8) would inherit none of the rate-limit handling or
scope revalidation that the current client gets for free from its library, and both failures are
invisible on a small test library. And #7, which relocates the token cache, cannot be expressed
as a clean modification until a spec exists for it to modify — OpenSpec deltas can only mark a
requirement `MODIFIED` when that requirement is already in the main spec.

## What Changes

- Add a `spotify-auth` capability spec documenting behavior that already exists: credential
  preconditions, the authorization flow and its scope set, scope revalidation against a cached
  authorization, token persistence, rate-limit resilience, and the `auth` command.
- Document in implementation-neutral terms, so the spec is reusable as the acceptance contract
  for #8 and does not name the current client library.
- Shape the token-persistence requirement so #7 can change it as a single `MODIFIED` requirement.
- **No behavior changes and no source changes.** Anything that looks wrong is filed separately;
  #13 is the first instance.

## Capability naming

Named `spotify-auth`, not `auth`. The tool authenticates to three services and only one of them
uses an interactive authorization flow:

| Service | Mechanism | Already specified in |
|---|---|---|
| Spotify | OAuth authorization code, browser consent, refresh, scopes | *nothing* — this change |
| Discogs | Static personal access token | `credentials` (storage), `genre-providers` (opt-in, rate limits) |
| MusicBrainz | No credential; User-Agent only | `genre-providers` |

A capability called `auth` would imply it owns all three and leave a reader looking for Discogs
credential handling in the wrong file. The narrower name keeps the boundary honest, and this
spec's Purpose points at the specs that own the other two.

## Capabilities

### New Capabilities
- `spotify-auth`: How the tool obtains and retains authorization to act on a user's Spotify
  account — required credentials, the scopes it requests and why, when a cached authorization is
  reused versus re-obtained, and how it behaves when the service rate-limits it.

### Modified Capabilities
<!-- None. This change documents existing behavior; no existing requirement changes. -->

## Impact

- **Specs**: adds `openspec/specs/spotify-auth/spec.md` on archive. No existing spec is modified.
- **Code**: none. No file under `src/` or `tests/` is touched.
- **Verification**: relies on `tests/test_auth.py` and `tests/test_cli.py`, plus direct probes of
  the client library for the defaults this repo depends on but does not set itself.
- **Downstream**: unblocks the remaining acceptance criteria for #8, and lets #7 land as a
  one-requirement diff instead of introducing and mutating a capability in the same change.
