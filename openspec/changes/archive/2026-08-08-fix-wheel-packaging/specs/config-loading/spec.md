## Purpose

Defines how the tool locates, layers, and loads its default and user configuration so
that the default genre/decade rules are always available regardless of how the package
was installed (wheel, pipx, editable, or source clone), and so users can persist their
own settings in a standard home-directory location instead of passing `--config` on
every invocation.

## ADDED Requirements

### Requirement: Bundled default config is available for every install method

The tool SHALL ship its default configuration as a package resource and load it
from that resource, so the default config is available whenever the package is
importable — including wheel and `pipx` installs — without depending on the
current working directory or on the source tree layout.

#### Scenario: Wheel install run from an arbitrary directory
- **WHEN** the package is installed from a built wheel and `spotify-sorter sort`
  is invoked from a directory that is not a source clone and contains no
  `config/` folder
- **THEN** the tool loads its bundled default configuration successfully
- **AND** does not raise `FileNotFoundError`

#### Scenario: Editable/source-clone install
- **WHEN** the package is installed editable (`pip install -e`) or run from a
  source clone
- **THEN** the tool loads the same bundled default configuration as a wheel
  install would

#### Scenario: No user config supplied
- **WHEN** `Config.load()` is called with no explicit path
- **THEN** the tool returns configuration populated entirely from the bundled
  default resource

### Requirement: Configuration is layered by a deterministic precedence chain

The tool SHALL build configuration by deep-merging up to four layers, each merged over
the previous so that a later layer overrides only the keys it sets and inherits the
rest. From lowest to highest precedence:

1. the bundled default (always present),
2. the user config file at `~/.config/spotify-sorter/config.yaml` (honoring
   `$XDG_CONFIG_HOME` when set), if it exists,
3. the file named by the `$SPOTIFY_SORTER_CONFIG` environment variable, if set,
4. the file passed via `--config <path>`, if given.

Each user layer may be partial. Absent layers are skipped without error.

#### Scenario: No user layers present
- **WHEN** no home config exists, no env var is set, and no `--config` is passed
- **THEN** the tool returns configuration populated entirely from the bundled default

#### Scenario: Home config only
- **WHEN** `~/.config/spotify-sorter/config.yaml` exists and sets a subset of options,
  and neither the env var nor `--config` is provided
- **THEN** the keys it sets take its values
- **AND** all unset keys retain their bundled default values

#### Scenario: XDG_CONFIG_HOME override
- **WHEN** `$XDG_CONFIG_HOME` is set to a directory containing
  `spotify-sorter/config.yaml`
- **THEN** the tool reads the user config from that directory rather than from
  `~/.config`

#### Scenario: Flag overrides home and env
- **WHEN** a home config, a `$SPOTIFY_SORTER_CONFIG` file, and a `--config` file all set
  the same key to different values
- **THEN** the value from `--config` wins for that key
- **AND** keys set only in the home or env layer still apply

#### Scenario: Explicitly named config path is missing
- **WHEN** the user passes `--config <path>`, or sets `$SPOTIFY_SORTER_CONFIG`, to a file
  that does not exist
- **THEN** the tool raises a clear `FileNotFoundError` naming the missing path

#### Scenario: Home config is absent
- **WHEN** no file exists at the resolved home-config location
- **THEN** the tool proceeds using the remaining layers without raising
