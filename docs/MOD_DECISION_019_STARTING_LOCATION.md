# Decision 019: Capture the Immutable Starting Location

- Status: Accepted
- Date: 2026-08-15

## Decision

When a Rat Race run identity is first created, capture the starting character's
current tile as immutable run evidence. Export it as
`character.startingLocation` with integer `x`, `y`, and `z`, the precision-safe
BuildingDef ID when the tile is inside a building, capture UTC and world age,
and an explicit partial-history flag.

When the captured building or tile matches a registered TGSRR outpost or
landmark, the evidence also includes its stable TGSRR ID, kind, and registry
version. Unknown or ordinary spawn buildings retain no invented stable ID.

The mod does not infer a town, spawn-region name, or other presentation label.
Those interpretations belong to the website and its versioned catalogue.

## Existing saves

If TGSRR creates a run identity for a character that has already survived for
any positive time, the observed location is retained but marked `partial`.
It proves only where tracking began, not where that character originally
spawned.

## Consequences

- A new development run-state schema is required because the value is immutable
  and cannot be reconstructed for an existing tracked run.
- The website validates and preserves the raw evidence.
- Future authoritative run-data tables can index the coordinates and resolve
  them against versioned website geography without rewriting the submission.
- Deployment installs stable outpost and landmark catalogue records plus their
  Build 42.20 anchors, bounds, and raw BuildingDef mappings. A later game build
  adds a new mapping rather than changing the stable TGSRR identity.
