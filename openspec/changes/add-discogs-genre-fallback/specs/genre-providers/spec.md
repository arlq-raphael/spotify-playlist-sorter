## Purpose

Resolve each track's genres from an ordered set of sources (Spotify and Discogs) so that classification
uses the best available data, with graceful fallback when a source is unavailable or returns nothing.

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

### Requirement: Spotify genre provider
The system SHALL provide a Spotify source that returns each track's artist genres, fetched in batches.

#### Scenario: Spotify genres resolved
- **WHEN** the Spotify provider is consulted for a track whose artist has genres
- **THEN** it returns those genres

### Requirement: Discogs genre provider
The system SHALL provide a Discogs source that, for a track, searches Discogs by artist and track title
and returns the best-matching release's genre and style values.

#### Scenario: Discogs styles resolved
- **WHEN** the Discogs provider is consulted and a matching release exists
- **THEN** it returns that release's genre and style values

#### Scenario: No Discogs match
- **WHEN** no matching release is found
- **THEN** the Discogs provider returns an empty genre set (so resolution falls through)

### Requirement: Discogs is opt-in and token-gated
The Discogs provider SHALL require a Discogs personal access token. When no token is configured the
provider SHALL be skipped (with a user-visible notice) rather than causing an error, and resolution SHALL
continue with the remaining providers.

#### Scenario: No token configured
- **WHEN** the provider order includes Discogs but no token is set
- **THEN** the Discogs provider is skipped and the system notifies the user
- **AND** genre resolution proceeds using the other providers

### Requirement: Respect Discogs rate limits and identify the client
The Discogs provider SHALL send a unique `User-Agent` on every request and SHALL stay within Discogs'
documented rate limit, waiting and retrying when the API signals the limit is reached.

#### Scenario: Rate limit signalled
- **WHEN** Discogs responds that the rate limit is exceeded
- **THEN** the provider waits and retries rather than failing the run

### Requirement: Cache Discogs lookups
The Discogs provider SHALL cache results by artist and title so the same query is not repeated within a
run (and ideally across runs), bounding the number of API calls.

#### Scenario: Repeated lookup served from cache
- **WHEN** two tracks resolve to the same artist+title Discogs query
- **THEN** the API is queried at most once for that query
