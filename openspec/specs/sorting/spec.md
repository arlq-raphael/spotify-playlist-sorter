# sorting Specification

## Purpose
Turn a user's Liked Songs into tidy bucket playlists: read the saved library, classify each
track independently along one or more dimensions (genre, decade), and apply the result to the
user's playlists idempotently, so the command can be re-run at any time to file only what is
new without ever duplicating or destroying existing content.
## Requirements
### Requirement: Read the saved library

The system SHALL read the user's saved ("liked") tracks in full, continuing until the entire
library has been retrieved regardless of its size. For each track it SHALL capture the track
identifier, title, contributing artists, album release year, duration, and ISRC where the
source provides them.

The system SHALL support restricting a run to the N most recently saved tracks, so a user can
rehearse a run against a small slice of their library.

#### Scenario: Library larger than one page
- **WHEN** the user's saved library contains more tracks than a single API response returns
- **THEN** the system retrieves every saved track before classifying

#### Scenario: Run restricted to the most recent saves
- **WHEN** the user requests a run limited to N tracks
- **THEN** the system processes only the N most recently saved tracks

#### Scenario: Entry without a usable track identifier
- **WHEN** a saved entry has no track identifier (for example a local file or a track
  unavailable in the user's market)
- **THEN** the system skips that entry and continues with the rest of the library
- **AND** does not fail the run

#### Scenario: Album release date is absent or unreadable
- **WHEN** a track's album has no release date, or has one whose leading characters cannot be
  read as a year number
- **THEN** the track is treated as having no release year
- **AND** the run continues with the remaining tracks

### Requirement: Assign a genre bucket by ordered, first-match-wins rules

The system SHALL assign a track to a genre bucket by evaluating the configured buckets in
their configured order and selecting the FIRST bucket for which any of its match terms occurs
as a substring of any of the track's genres. A match term need not equal a whole genre string.

Because evaluation stops at the first matching bucket, ordering is significant: a bucket
listed earlier takes precedence over any later bucket that would also match.

#### Scenario: Earlier bucket wins over a later one
- **WHEN** a track's genres would satisfy the match terms of two different buckets
- **THEN** the track is assigned to whichever of the two is configured first
- **AND** the later bucket is not considered for that track

#### Scenario: Match term occurs inside a longer genre string
- **WHEN** a track's genre is a more specific string that contains a bucket's match term as a
  substring
- **THEN** the bucket matches that track

### Requirement: Normalize genre case before matching

Bucket matching compares strings directly and does NOT fold case at comparison time.
Case-insensitive behavior is therefore a property of normalization, and the system SHALL
guarantee it at both ends: every genre SHALL be normalized to lower case at the point it is
resolved, by every genre source without exception, and every configured match term SHALL be
normalized to lower case when configuration is loaded.

This invariant is load-bearing and silent when broken: a genre that reaches matching with any
upper-case character cannot match any bucket, so the affected tracks are misfiled into the
unmatched-genre bucket with no error raised and nothing reported. Any genre source added in
future SHALL normalize its output the same way.

#### Scenario: Source returns genres in mixed case
- **WHEN** a genre source returns a genre containing upper-case characters
- **THEN** the genre is normalized to lower case before matching
- **AND** it matches the same bucket it would have matched had the source returned it in lower
  case

#### Scenario: User writes match terms in mixed case
- **WHEN** a user configures a bucket whose match terms contain upper-case characters
- **THEN** those terms match the same genres they would have matched in lower case

#### Scenario: Every source normalizes identically
- **WHEN** the same track is resolved by different genre sources that report the same genre in
  different capitalization
- **THEN** the track is assigned to the same bucket regardless of which source resolved it

### Requirement: Fall back when no genre bucket matches

The system SHALL distinguish between a track whose genres matched no configured bucket and a
track for which no genres could be determined at all, and SHALL provide a separately
configurable fallback bucket for each case.

Either fallback MAY be disabled by configuration, in which case a track in that situation
receives no genre placement and is left unsorted on the genre dimension.

#### Scenario: Genres present but none match a bucket
- **WHEN** a track has one or more genres and none of them satisfies any configured bucket
- **THEN** the track is assigned to the configured unmatched-genre bucket

#### Scenario: No genres could be determined
- **WHEN** no genres could be determined for a track
- **THEN** the track is assigned to the configured no-genre bucket

#### Scenario: A fallback is disabled
- **WHEN** the applicable fallback bucket is disabled in configuration
- **THEN** the track receives no genre placement
- **AND** the run continues normally

### Requirement: Derive a decade bucket from the album release year

The system SHALL derive a track's decade from its album release year and SHALL name the
resulting bucket using the configured decade format.

A configurable floor year MAY be set, in which case release years earlier than the floor are
grouped into the floor's decade rather than producing many sparsely populated early buckets.
The resulting bucket is named for the floor's decade, so a track older than the floor appears
in a bucket named for a later decade than its own. When no floor is configured, early years
produce their own decade buckets.

#### Scenario: Year maps to its decade
- **WHEN** a track's album release year falls within a decade
- **THEN** the track is assigned to that decade's bucket, named using the configured format

#### Scenario: Track has no release year
- **WHEN** a track has no album release year
- **THEN** the track receives no decade placement

#### Scenario: Year earlier than the configured floor
- **WHEN** a track's release year is earlier than the configured floor year
- **THEN** the track is assigned to the bucket for the floor year's decade, not to a bucket for
  its own decade
- **AND** no bucket is created for any decade earlier than the floor's

#### Scenario: No floor configured
- **WHEN** no floor year is configured and a track's release year falls in an early decade
- **THEN** the track is assigned to the bucket for its own decade

### Requirement: Select which dimensions run

The system SHALL let the user choose which classification dimensions to apply to a run, and
SHALL apply every selected dimension. Dimensions are independent: each one is evaluated
against the track on its own, so a single track MAY be placed into one playlist per selected
dimension.

A dimension MAY be disabled by configuration, which makes it unavailable for selection.

#### Scenario: Both dimensions selected
- **WHEN** the user selects both the genre and decade dimensions and a track produces a bucket
  for each
- **THEN** the track is placed into both the genre playlist and the decade playlist

#### Scenario: Single dimension selected
- **WHEN** the user selects only one dimension
- **THEN** only that dimension's playlists are planned, and the other dimension's buckets are
  not produced

#### Scenario: Unknown dimension requested
- **WHEN** the user requests a dimension the system does not provide
- **THEN** the system fails with an error naming the dimension and listing the available ones
- **AND** makes no changes to the user's playlists

#### Scenario: Disabled dimension requested
- **WHEN** the user requests a dimension that configuration has disabled
- **THEN** the system fails in the same way as for an unknown dimension

### Requirement: Plan target playlists before making any change

The system SHALL compute the complete set of intended placements before modifying anything, so
the effect of a run can be reported up front. The target playlist name SHALL be the configured
playlist prefix followed by the bucket name.

Within a single target playlist, a track SHALL appear at most once no matter how many times it
was placed there. Tracks that produced no bucket on any selected dimension SHALL be recorded as
skipped, and the count reported to the user.

#### Scenario: Playlist prefix applied
- **WHEN** a playlist prefix is configured and a track is assigned to a bucket
- **THEN** the target playlist name is the prefix followed by the bucket name

#### Scenario: Same track placed twice in one playlist
- **WHEN** the same track would be placed into the same target playlist more than once
- **THEN** the plan contains that track exactly once for that playlist

#### Scenario: Track matches no dimension
- **WHEN** a track produces no bucket on any selected dimension
- **THEN** the plan records the track as skipped
- **AND** the number of skipped tracks is reported to the user

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

### Requirement: Only match playlists the user owns

When matching a planned playlist name against existing playlists, the system SHALL consider
only playlists owned by the authenticated user. A playlist with the same name owned by someone
else — for example one the user follows — SHALL NOT be matched, and SHALL NOT be created into
or otherwise modified.

#### Scenario: Same-named playlist owned by another user
- **WHEN** the user follows a playlist whose name equals a planned playlist name, and owns no
  playlist by that name
- **THEN** the system creates its own playlist with that name
- **AND** does not add tracks to the followed playlist

### Requirement: Dry run reports without changing anything

The system SHALL provide a dry-run mode that reports exactly what a real run would do —
which playlists would be created and how many tracks would be added to each — while
performing no write of any kind.

#### Scenario: Dry run for a playlist that would be created
- **WHEN** a dry run is performed and a planned playlist does not exist
- **THEN** the system reports that the playlist would be created, with the number of tracks it
  would receive
- **AND** no playlist is created

#### Scenario: Dry run for an existing playlist that would gain tracks
- **WHEN** a dry run is performed and a planned playlist exists but lacks some planned tracks
- **THEN** the system reports how many tracks would be added
- **AND** the playlist's contents are left unchanged
