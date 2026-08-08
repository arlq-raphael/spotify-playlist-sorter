# spotify-auth Specification

## Purpose
Obtain and retain the user's authorization to read their Spotify library and modify their
playlists: establish that the required app credentials are present, run an interactive consent
flow when no usable authorization is held, persist the result so consent is not repeated, and
keep working when the service rate-limits the client.

Scoped to Spotify, the only service the tool authorizes interactively. The Discogs personal
access token is covered by the `credentials` capability (how it is stored and resolved) and the
`genre-providers` capability (that its absence skips the source rather than failing); the ISRC
lookup source needs no credential at all.
## Requirements
### Requirement: Require app credentials before contacting the service

The system SHALL require three values before attempting authorization: the application's client
identifier, its client secret, and the redirect URI registered for it. When any of them is
missing the system SHALL fail immediately, before opening a browser or issuing any network
request, and SHALL name every missing value rather than only the first one found.

How those values are supplied and layered is governed by the `credentials` capability; this
requirement governs only that they are present and what happens when they are not.

#### Scenario: All credentials missing
- **WHEN** none of the three values is available from any source
- **THEN** the system exits with an error naming all three
- **AND** no browser is opened and no request is made to the service

#### Scenario: Some credentials missing
- **WHEN** some of the three values are available and others are not
- **THEN** the error names exactly those that are missing

#### Scenario: All credentials present
- **WHEN** all three values are available
- **THEN** the system builds an authorized client without contacting the service or opening a
  browser until an operation actually needs it

### Requirement: Request the scopes the tool's commands require

The system SHALL request exactly the permissions its commands need: reading the user's saved
library, modifying the user's saved library, reading the user's private playlists, and modifying
the user's public and private playlists.

Library *modification* is required only so that duplicate removal can un-save redundant copies.
It is requested at authorization time regardless of which command runs, because consent is
obtained once and reused across commands.

#### Scenario: Consent covers library modification
- **WHEN** the user authorizes the application
- **THEN** the granted authorization permits un-saving tracks from the saved library
- **AND** duplicate removal can run later without a second consent step

#### Scenario: Consent covers private playlists
- **WHEN** the user authorizes the application
- **THEN** the granted authorization permits reading and modifying playlists that are not public

### Requirement: Re-obtain authorization when the retained one is insufficient

The system SHALL compare the permissions a retained authorization carries against those it
currently requires, and SHALL discard the retained authorization and obtain fresh consent
whenever the required permissions are not all covered by it. A retained authorization that
covers more than is currently required SHALL be reused rather than discarded.

Without this check the tool would present a retained authorization that the service then
rejects for the operation being attempted, surfacing as a permission failure from the service
rather than as a prompt to re-consent.

#### Scenario: Retained authorization lacks a required permission
- **WHEN** the tool requires a permission that the retained authorization does not carry — for
  example after a new command widened what the tool needs
- **THEN** the retained authorization is discarded and the user is asked to consent again
- **AND** the user is not required to remove any file by hand for this to happen

#### Scenario: Retained authorization carries more than is required
- **WHEN** the retained authorization covers every currently required permission and some others
- **THEN** it is reused without asking the user to consent again

### Requirement: Obtain consent interactively on first use

When no usable authorization is retained, the system SHALL obtain one through an interactive
authorization-code flow, opening the user's browser so they can grant consent, and SHALL
complete the exchange by receiving the result at the registered redirect URI.

#### Scenario: No authorization retained
- **WHEN** an operation needs authorization and none is retained
- **THEN** the system opens the user's browser to the service's consent page
- **AND** completes authorization using the result delivered to the registered redirect URI

### Requirement: Retain authorization between runs

The system SHALL persist the authorization it obtains and reuse it on later runs, so a user
consents once rather than on every invocation. A persisted authorization that has expired SHALL
be renewed without asking the user to consent again.

The authorization is persisted in the directory the command is run from. Because it grants
ongoing access to the user's account, it is excluded from version control.

#### Scenario: Second run reuses the retained authorization
- **WHEN** a command is run after a previous run authorized successfully, from the same directory
- **THEN** no browser is opened and the retained authorization is used

#### Scenario: Retained authorization has expired
- **WHEN** the retained authorization has passed its expiry but can still be renewed
- **THEN** the system renews it without prompting the user

#### Scenario: Command run from a different directory
- **WHEN** a command is run from a directory other than the one that holds the retained
  authorization
- **THEN** no authorization is found there and the user is asked to consent again

### Requirement: Withstand rate limiting

When the service reports that the client has exceeded its rate limit, the system SHALL wait and
retry rather than failing the run, and SHALL honor the delay the service asks for instead of
choosing its own. Retries SHALL be bounded, so a persistently failing request eventually
surfaces an error rather than retrying forever.

This matters in proportion to library size: a run over a large saved library issues enough
requests to be rate-limited routinely, while a small one may never trigger it at all.

#### Scenario: Service signals the rate limit
- **WHEN** a request is rejected because the rate limit was exceeded, and the response states how
  long to wait
- **THEN** the system waits at least that long and retries the request
- **AND** the run continues rather than failing

#### Scenario: Repeated failure
- **WHEN** a request continues to fail after the permitted number of retries
- **THEN** the system stops retrying and reports the failure

### Requirement: Provide a command that authorizes and exits

The system SHALL provide a command that performs authorization on its own, confirms that it
succeeded, and exits without reading the library or modifying any playlist — so a user can
complete consent as a deliberate step rather than as a side effect of their first real run.

#### Scenario: Authorization command succeeds
- **WHEN** the user runs the authorization command and consent completes
- **THEN** the system confirms success and reports where the authorization was retained
- **AND** no playlist is created or modified
