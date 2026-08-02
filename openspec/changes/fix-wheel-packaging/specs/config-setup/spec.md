## Purpose

Provides a `configure` command that helps users create their configuration without
hand-writing YAML: an interactive wizard that collects the common settings, writes a
minimal user config to the standard home location, and records an optional Discogs token
in `.env` — keeping secrets out of the config file.

## ADDED Requirements

### Requirement: Interactive configure wizard writes a user config

The tool SHALL provide a `configure` command that interactively prompts for the common
settings and writes them to the user config location resolved by the config-loading
capability (`~/.config/spotify-sorter/config.yaml`, honoring `$XDG_CONFIG_HOME`). Each
prompt SHALL show the current default and accept it on empty input. After writing, the
command SHALL print the absolute path of the file it wrote.

#### Scenario: Wizard writes chosen settings
- **WHEN** the user runs `configure` and answers the prompts (e.g. a playlist prefix and
  private playlists)
- **THEN** the tool writes a config file at the resolved user-config path containing those
  settings
- **AND** prints the path that was written

#### Scenario: Empty answer keeps the default
- **WHEN** the user presses Enter at a prompt without typing a value
- **THEN** that setting is left at its default and is not written as an override

### Requirement: Generated config is minimal and inherits unset values

The `configure` command SHALL write only the settings the user changed from their
defaults, producing a partial config. Settings left at their default SHALL be omitted so
they continue to inherit from the bundled default via the config-loading precedence chain.

#### Scenario: Only changed settings are persisted
- **WHEN** the user changes only the playlist prefix and accepts every other default
- **THEN** the written file contains the playlist prefix
- **AND** does not contain the unchanged settings
- **AND** a subsequent load produces the user's prefix plus the bundled defaults for
  everything else

### Requirement: Secrets are written to .env, never to the config file

When the wizard collects a Discogs API token, the tool SHALL write it to a `.env` file as
`DISCOGS_TOKEN` and SHALL NOT write the token into the YAML config. Token entry SHALL be
masked (not echoed to the terminal).

#### Scenario: Discogs token recorded in .env
- **WHEN** the user opts to enable Discogs and enters a token
- **THEN** the token is written to `.env` as `DISCOGS_TOKEN=...`
- **AND** the token does not appear in the written YAML config

#### Scenario: Existing .env token updated in place
- **WHEN** `.env` already contains a `DISCOGS_TOKEN` line and the user enters a new token
- **THEN** the existing line is updated rather than duplicated

#### Scenario: Declining Discogs writes no token
- **WHEN** the user declines to enable Discogs
- **THEN** no `.env` write for `DISCOGS_TOKEN` occurs

### Requirement: Existing config is not overwritten without confirmation

The `configure` command SHALL refuse to overwrite an existing user config file unless the
user passes `--force`, and SHALL report that the file already exists.

#### Scenario: Refuses to clobber
- **WHEN** a user config already exists at the target path and `configure` is run without
  `--force`
- **THEN** the tool does not modify the file
- **AND** reports that the file exists and how to overwrite it (exit non-zero)

#### Scenario: Force overwrites
- **WHEN** the same situation occurs and `--force` is passed
- **THEN** the tool overwrites the file with the new settings

### Requirement: Configure is scriptable and non-interactive-capable

Every prompt SHALL have an equivalent command-line flag, and a non-interactive mode SHALL
write a config from flags and defaults without reading from standard input, so the command
can be used in scripts, CI, and tests.

#### Scenario: Non-interactive run from flags
- **WHEN** the user runs `configure` in non-interactive mode with settings supplied as
  flags
- **THEN** the tool writes the config from those flags without prompting
- **AND** unsupplied settings are left at their defaults (omitted from the file)
