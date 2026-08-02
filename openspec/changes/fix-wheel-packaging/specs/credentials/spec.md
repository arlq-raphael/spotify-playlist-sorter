## Purpose

Defines how the tool stores and loads secret credentials (the Discogs token and,
optionally, the Spotify app credentials) in a per-user credentials file kept separate
from the non-secret preferences config — mirroring the aws-cli split of a config file
from a credentials file — so a globally-installed CLI has a persistent, owner-only secret
store rather than a working-directory-bound `.env`.

## ADDED Requirements

### Requirement: Secrets load from a per-user credentials file and the environment

The tool SHALL load secret values (`DISCOGS_TOKEN`, and when present the Spotify app
credentials `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` / `SPOTIPY_REDIRECT_URI`) from a
per-user credentials file located at `~/.config/spotify-sorter/credentials` (honoring
`$XDG_CONFIG_HOME`), as `KEY=VALUE` lines. Secrets SHALL resolve with the following
precedence, highest first: a value already present in the process environment, then a
project-local `./.env`, then the per-user credentials file. A value set at a higher layer
SHALL NOT be overridden by a lower layer.

#### Scenario: Token supplied only by the credentials file
- **WHEN** `DISCOGS_TOKEN` is unset in the environment and absent from `./.env`, but the
  per-user credentials file defines it
- **THEN** the tool uses the token from the credentials file

#### Scenario: Environment overrides the credentials file
- **WHEN** `DISCOGS_TOKEN` is set in the process environment and also present in the
  credentials file with a different value
- **THEN** the tool uses the environment value

#### Scenario: Project .env overrides the credentials file
- **WHEN** a value is present in both `./.env` and the per-user credentials file, and not
  set in the environment
- **THEN** the tool uses the `./.env` value

#### Scenario: Missing credentials file is not an error
- **WHEN** no credentials file exists at the resolved location
- **THEN** the tool proceeds using the environment and `./.env` only, without raising

### Requirement: Secrets are never read from or written to the preferences config

The tool SHALL keep secrets out of the preferences configuration: it SHALL NOT read
credential values from the YAML config, nor write any secret into it. Secrets belong only
in the environment, `./.env`, or the credentials file.

#### Scenario: Config file carries no secrets
- **WHEN** the tool loads configuration
- **THEN** credential values are sourced only from the environment / `.env` / credentials
  file
- **AND** no secret is read from or written to the preferences YAML

### Requirement: The credentials file is written with owner-only permissions

When the tool creates or updates the credentials file, it SHALL set the file permissions
to owner read/write only (`0600`), and SHALL update an existing key in place rather than
duplicating it.

#### Scenario: New credentials file is owner-only
- **WHEN** the tool writes a credentials file that did not previously exist
- **THEN** the file's permissions are `0600`

#### Scenario: Existing key updated in place
- **WHEN** the credentials file already contains a key and the tool writes a new value for
  it
- **THEN** the existing line is replaced rather than duplicated
- **AND** unrelated lines are preserved
