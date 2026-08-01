## Purpose

Resolve each track's genres from an ordered set of sources (an exact ISRC lookup, Discogs, and Spotify)
so that classification uses the best available data, preferring exact identification and degrading
gracefully when a source is unavailable or returns nothing.

## ADDED Requirements

### Requirement: Ordered provider resolution
The system SHALL resolve a track's genres by consulting configured providers in priority order and using
the FIRST provider that returns a non-empty genre set. The order SHALL be configurable.

#### Scenario: Higher-priority provider wins
- **WHEN** the first provider returns genres for a track
- **THEN** those genres are used and lower-priority providers are not consulted for that track

#### Scenario: Falls through to the next provider
- **WHEN** the first provider returns no genres for a track
- **THEN** the system consults the next provider in order

#### Scenario: No provider resolves genres
- **WHEN** no provider returns genres for a track
- **THEN** the track is treated as having no genre (existing no-genre-bucket fallback applies)

### Requirement: ISRC-first exact identification
When a track has an ISRC, the system SHALL attempt an exact lookup of that recording by ISRC and use the
resulting genres BEFORE any fuzzy artist/title matching. This exact step is preferred because an ISRC is
a globally unique recording identifier.

#### Scenario: ISRC yields genres
- **WHEN** a track has an ISRC and the exact lookup returns genres for it
- **THEN** those genres are used and no fuzzy search is performed for that track

#### Scenario: ISRC has no usable result
- **WHEN** a track has an ISRC but the lookup finds no recording or no genres
- **THEN** resolution falls through to the fuzzy providers

#### Scenario: No ISRC
- **WHEN** a track has no ISRC
- **THEN** the exact ISRC step is skipped and resolution uses the fuzzy providers

### Requirement: Discogs genre provider
The system SHALL provide a Discogs source that searches by artist and track title and returns the
best-matching release's genre and style values.

#### Scenario: Discogs styles resolved
- **WHEN** the Discogs provider is consulted and a matching release exists
- **THEN** it returns that release's genre and style values

#### Scenario: No Discogs match
- **WHEN** no matching release is found
- **THEN** the Discogs provider returns an empty genre set (so resolution falls through)

### Requirement: Spotify genre provider
The system SHALL provide a Spotify source that returns each track's artist genres, fetched in batches.

#### Scenario: Spotify genres resolved
- **WHEN** the Spotify provider is consulted for a track whose artist has genres
- **THEN** it returns those genres

### Requirement: Credentialed sources are opt-in and degrade gracefully
A genre source that requires a credential (the Discogs personal access token) SHALL be skipped with a
user-visible notice when the credential is not configured, rather than causing an error, and resolution
SHALL continue with the remaining sources.

#### Scenario: No Discogs token configured
- **WHEN** the provider order includes Discogs but no token is set
- **THEN** the Discogs source is skipped and the system notifies the user
- **AND** genre resolution proceeds using the other sources

### Requirement: Identify the client and respect rate limits
Every external genre source (Discogs, and the ISRC lookup) SHALL send a unique `User-Agent` on every
request and SHALL stay within that source's published rate limit, waiting and retrying when the API
signals the limit is reached.

#### Scenario: Rate limit signalled
- **WHEN** an external source responds that the rate limit is exceeded
- **THEN** the source waits and retries rather than failing the run

### Requirement: Cache external lookups
External genre lookups SHALL be cached by their query key (ISRC, or artist+title) so the same lookup is
not repeated within a run, and ideally across runs, bounding the number of API calls.

#### Scenario: Repeated lookup served from cache
- **WHEN** two tracks resolve to the same lookup key
- **THEN** the external API is queried at most once for that key
