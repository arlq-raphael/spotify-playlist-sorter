## Purpose

Detect and remove duplicate tracks in a user's Spotify Liked Songs — both exact duplicates of the same
recording and alternate versions of one song — keeping a single copy per song while preserving the
integrity of the sorted playlists.

## ADDED Requirements

### Requirement: Detect and group duplicate liked songs
The system SHALL scan the user's Liked Songs and group tracks that represent the same song, matching on
normalized title and primary artist (case-insensitive, ignoring parenthetical `feat.`/`with` credits
and trailing version tags such as "- Remastered", "- Live", "- Radio Edit").

#### Scenario: Two saves of the same recording are grouped
- **WHEN** the library contains the same song under two different track IDs
- **THEN** the system places both track IDs in one duplicate group

#### Scenario: Distinct songs are not grouped
- **WHEN** two tracks share neither normalized title nor primary artist
- **THEN** the system SHALL keep them in separate groups

### Requirement: Classify duplicate groups
The system SHALL classify each duplicate group as either an EXACT duplicate (same recording — matching
normalized title, primary artist, and track duration within a small tolerance) or a VERSION PAIR (same
song but a different version, indicated by a version tag or a materially different duration).

#### Scenario: Same duration marks an exact duplicate
- **WHEN** grouped tracks have durations within the tolerance
- **THEN** the system SHALL classify the group as an exact duplicate

#### Scenario: Different duration marks a version pair
- **WHEN** grouped tracks differ in duration beyond the tolerance, or one carries a version tag
- **THEN** the system SHALL classify the group as a version pair

### Requirement: Report before modifying
The system SHALL, by default, only report the duplicate groups it finds and make no changes. It SHALL
require an explicit apply flag before removing anything.

#### Scenario: Default run is read-only
- **WHEN** the dedupe command is run without the apply flag
- **THEN** the system SHALL list the duplicate groups and their classification
- **AND** SHALL NOT remove any track from the library or any playlist

#### Scenario: Apply flag enables removal
- **WHEN** the dedupe command is run with the apply flag
- **THEN** the system SHALL remove redundant copies according to the removal rules

### Requirement: Keep one copy per song
When applying, the system SHALL remove all but one copy from each duplicate group. For an exact
duplicate it MAY keep any copy. For a version pair it SHALL keep the original (the untagged or earliest
release) and remove the tagged variant (remaster, live, edit, extended, remix, single).

#### Scenario: Exact duplicate reduced to one
- **WHEN** applying to an exact-duplicate group of N copies
- **THEN** exactly one copy SHALL remain saved in Liked Songs

#### Scenario: Version pair keeps the original
- **WHEN** applying to a version pair where one track is untagged and the other is a remaster/live/edit
- **THEN** the untagged original SHALL remain and the tagged variant SHALL be removed

### Requirement: Do not remove unresolved version pairs
When a version pair's original cannot be confidently determined (e.g. both are tagged, or durations
conflict with no clear original), the system SHALL keep both copies and report the group as unresolved
rather than guess.

#### Scenario: Ambiguous pair is preserved
- **WHEN** applying to a version pair whose original is indeterminate
- **THEN** both copies SHALL remain and the group SHALL be reported as unresolved

### Requirement: Purge removed copies from sorted playlists
When the system removes a track from Liked Songs, it SHALL also remove that track from any genre/decade
playlists it was placed in, so no orphaned copy remains in a sorted playlist.

#### Scenario: Removed duplicate is cleared from its playlists
- **WHEN** a duplicate copy that also appears in one or more sorted playlists is removed from Liked Songs
- **THEN** that track SHALL also be removed from each of those playlists
