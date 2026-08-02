## Purpose

Defines how the tool locates and loads its default and user configuration so that
the default genre/decade rules are always available regardless of how the package
was installed (wheel, pipx, editable, or source clone).

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

### Requirement: Explicit user config is merged over the bundled default

When the user supplies a config path, the tool SHALL read that file from the
filesystem and deep-merge it over the bundled default, so a partial user config
overrides only the keys it sets and inherits the rest.

#### Scenario: Partial user config
- **WHEN** the user passes `--config <path>` to a file that sets only a subset of
  options
- **THEN** the overridden keys take the user's values
- **AND** all unset keys retain their bundled default values

#### Scenario: Missing user config path
- **WHEN** the user passes `--config <path>` to a file that does not exist
- **THEN** the tool raises a clear `FileNotFoundError` naming the missing path
