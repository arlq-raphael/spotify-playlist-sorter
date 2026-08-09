## MODIFIED Requirements

### Requirement: ISRC-first exact identification
When a track has an ISRC, the system SHALL attempt an exact lookup of that recording by ISRC and use the
resulting genres BEFORE any fuzzy artist/title matching. This exact step is preferred because an ISRC is
a globally unique recording identifier.

Genres belong to the recording an ISRC identifies, so the system SHALL take them from that recording.
An ISRC MAY identify more than one recording; where it does, the system SHALL use the first recording
identified rather than combining genres across all of them, so the work done per track stays
proportional to a single recording no matter how many an ISRC resolves to.

#### Scenario: ISRC yields genres
- **WHEN** a track has an ISRC and the exact lookup returns genres for it
- **THEN** those genres are used and no fuzzy search is performed for that track

#### Scenario: ISRC has no usable result
- **WHEN** a track has an ISRC but the lookup finds no recording or no genres
- **THEN** resolution falls through to the fuzzy providers

#### Scenario: No ISRC
- **WHEN** a track has no ISRC
- **THEN** the exact ISRC step is skipped and resolution uses the fuzzy providers

#### Scenario: ISRC identifies more than one recording
- **WHEN** a track's ISRC identifies several recordings
- **THEN** the genres of the first recording identified are used
- **AND** genres belonging to the other recordings are not merged into the result

#### Scenario: The identified recording carries no genres
- **WHEN** a track's ISRC identifies a recording and that recording has no genres
- **THEN** the track is treated as unresolved by this source and falls through to the fuzzy providers
- **AND** the empty result is retained so the same ISRC is not looked up again
