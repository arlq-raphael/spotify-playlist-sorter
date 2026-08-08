## 1. Verify each requirement against the current implementation

A task is done when every scenario in that requirement has been confirmed against the code and
against evidence — an existing test where one covers it, or a direct probe where none does.

Unlike the `sorting` backfill, much of this capability's behavior comes from the client library
rather than from this repo, so several scenarios were probed against the library. Where a
scenario cannot be observed without completing a live OAuth flow, that is stated rather than
claimed as observed.

- [x] 1.1 "Require app credentials before contacting the service" — all-missing exits
      (`test_get_client_missing_env_exits`); a fully-credentialed construction opens no browser
      and makes no request (`test_get_client_builds_with_env`). Partial-missing is untested,
      probed: with only the secret absent the error reads `Missing environment variables:
      SPOTIPY_CLIENT_SECRET` and names neither present value
- [x] 1.2 "Request the scopes the tool's commands require" —
      `test_scopes_include_library_modify_for_dedupe` covers the dedupe scope; the full set is
      untested, probed and confirmed to be exactly the five expected, including both
      private-playlist permissions
- [x] 1.3 "Re-obtain authorization when the retained one is insufficient" — no test; verified
      against the library. `validate_token` returns `None` when required scopes are not a subset
      of the retained ones, forcing re-consent. Probed with this repo's real scope strings:
      widening yields `False` (discard), narrowing yields `True` (reuse)
- [x] 1.4 "Obtain consent interactively on first use" — probed: browser-opening is enabled and
      the redirect URI resolves to the configured value. **Verified as configuration, not as
      observed behavior** — the browser actually opening needs a live flow
- [x] 1.5 "Retain authorization between runs" — probed: retained at a relative path, so
      resolution is working-directory dependent, and that path is git-ignored. Renewal-on-expiry
      verified by reading `validate_token`, which refreshes rather than re-prompting.
      **Renewal not observed live**
- [x] 1.6 "Withstand rate limiting" — no test; probed off the constructed client's retry policy:
      total 5, status forcelist `(429, 500, 502, 503, 504)`, `respect_retry_after_header` true,
      backoff factor 0.5. Confirms both halves — the service's requested delay is honored, and
      retries are bounded. **Not observed against live rate limiting**
- [x] 1.7 "Provide a command that authorizes and exits" — `test_cli_auth` covers the success
      message and exit code; that it modifies no playlist is structural, as the command issues
      only the current-user request

## 2. Confirm the spec is implementation-neutral

- [x] 2.1 Searched the delta for library, module, function, language, and wire-level permission
      names — zero hits
- [x] 2.2 Every scenario is a testable WHEN/THEN
- [x] 2.3 No requirement restates `credentials` or `config-loading`; secret resolution is
      referenced as owned elsewhere, not duplicated
- [x] 2.4 Named `spotify-auth` rather than `auth`, with the Purpose naming the specs that own
      Discogs and ISRC-source credentials. Only Spotify authorizes interactively; Discogs uses a
      static token owned by `credentials` and `genre-providers`, and the ISRC source needs none

## 3. Validate and check for regressions

- [x] 3.1 `openspec validate backfill-auth-spec --strict` passes
- [x] 3.2 Suite passes unchanged (99 passed, 98.71% coverage); `git status` shows no modification
      under `src/` or `tests/`

## 4. Follow-ups

- [x] 4.1 Filed #13 — the README tells users to delete the retained authorization by hand after a
      scope change, which the scope-subset check already handles. The spec documents the
      automatic behavior as-is; the README correction is filed separately
- [x] 4.2 Verified that token persistence is confined to one requirement: every location
      reference lives inside "Retain authorization between runs". The one mention elsewhere —
      the `auth` command reporting where the authorization was retained — is deliberately
      location-agnostic and stays true after #7. So #7 is a single `MODIFIED` requirement
- [x] 4.3 Recorded what #7 must update. **Two of the three scenarios**, not all three:
      "Second run reuses the retained authorization" loses its *same directory* qualifier, and
      "Command run from a different directory" has its outcome inverted from re-consent to
      reuse. "Retained authorization has expired" is pure renewal semantics and is untouched.
      The requirement prose changes too, and #7 introduces `$XDG_CONFIG_HOME` honoring and
      owner-only permissions that this spec has no equivalent for — those arrive as new
      scenarios within the modified requirement
