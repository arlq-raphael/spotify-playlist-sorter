## MODIFIED Requirements

### Requirement: Spotify genre provider
The system SHALL provide a Spotify source that returns each track's artist genres. Artists SHALL be
looked up individually: the platform no longer serves several artists in one request, so the source
SHALL NOT depend on batching being available.

Each distinct artist SHALL be looked up at most once per run however many tracks reference it.

Genres from this source describe the artist, not the recording, so every track crediting an artist
receives the same genres regardless of how that particular track sounds. This is a limitation of
the source rather than of the implementation, and it is why a recording-level source is consulted
first where one can identify the track.

#### Scenario: Spotify genres resolved
- **WHEN** the Spotify provider is consulted for a track whose artist has genres
- **THEN** it returns those genres

#### Scenario: One artist shared by many tracks
- **WHEN** several tracks in a run credit the same artist
- **THEN** that artist is looked up once, and every one of those tracks receives its genres

#### Scenario: Track with several artists
- **WHEN** a track credits more than one artist
- **THEN** the genres of all of them are combined, in the order the artists are credited, without
  repeating a genre

### Requirement: Persistently cache external lookups
External genre lookups SHALL be cached by their query key (ISRC, or artist+title), including empty
results, so the same lookup is not repeated within a run. The cache SHALL persist across runs so a
later run does not re-query tracks that were previously resolved or previously missed.

#### Scenario: Repeated lookup served from cache within a run
- **WHEN** two tracks resolve to the same lookup key in one run
- **THEN** the external API is queried at most once for that key

#### Scenario: Later run reuses the persisted cache
- **WHEN** a track's lookup key was resolved (or missed) in a previous run and appears again
- **THEN** the result is served from the persisted cache without querying the API

#### Scenario: An artist with no genres is remembered
- **WHEN** an artist lookup returns no genres, and a later run encounters that artist again
- **THEN** the empty result is served from the cache rather than re-queried
