## MODIFIED Requirements

### Requirement: Apply the plan idempotently

The system SHALL apply a plan by matching each target playlist by name, creating it only when
no match exists, and adding only those planned tracks not already present in it. Re-running
with an unchanged library SHALL therefore make no modifications.

Newly created playlists SHALL take their visibility from configuration, and SHALL be owned by the
authenticated user. Ownership is what makes the idempotency guarantee hold across runs: matching
is restricted to playlists that user owns, so a playlist created under any other owner would not
be matched on the next run and would be created again, indefinitely.

The system SHALL complete correctly regardless of how many playlists the user has, how many
tracks a target playlist already holds, or how many tracks a single run must add.

#### Scenario: Target playlist does not yet exist
- **WHEN** a planned playlist name matches none of the user's existing playlists
- **THEN** the system creates the playlist with the configured visibility
- **AND** the created playlist is owned by the authenticated user
- **AND** adds all of that playlist's planned tracks

#### Scenario: Target playlist exists and is missing some tracks
- **WHEN** a planned playlist already exists and contains some but not all of its planned tracks
- **THEN** the system adds only the tracks not already present
- **AND** leaves the tracks already in the playlist untouched

#### Scenario: Re-run with nothing new
- **WHEN** the command is run again and every planned track is already in its target playlist
- **THEN** the system makes no modifications
- **AND** reports each target playlist as already up to date

#### Scenario: A playlist created by a previous run is matched, not duplicated
- **WHEN** a run creates a target playlist and the command is run again
- **THEN** the second run matches the playlist the first run created
- **AND** does not create a second playlist of the same name

#### Scenario: Run adds more tracks than one request permits
- **WHEN** a single target playlist must receive more tracks than one API request accepts
- **THEN** the system still adds every planned track
