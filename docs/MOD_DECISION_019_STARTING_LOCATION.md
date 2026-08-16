# Decision 019: Capture Immutable Starting-Location Evidence

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

Before vanilla initializes the world, TGSRR also captures the spawn-region choice
as `character.chosenStartingRegion`. It preserves whether the player explicitly
selected a region or requested a random region, the resolved raw Project Zomboid
region ID, and capture UTC. This is distinct from the observed spawn tile.

TGSRR supplies a blind Random row above the available spawn regions. Selecting it
does not resolve or reveal a region on the spawn screen. TGSRR resolves it once,
immediately before the final Start action, then supplies that region to vanilla's
normal spawn-point selection. Returning to the spawn screen before Start does not
reveal or reroll it because it has not yet been resolved.

The mod does not infer a town or other presentation label from either evidence
record. Those interpretations belong to the website and its versioned catalogue.

## Existing saves

If TGSRR creates a run identity for a character that has already survived for
any positive time, the observed location is retained but marked `partial`.
It proves only where tracking began, not where that character originally
spawned.

## Consequences

- A new development run-state schema is required because the value is immutable
  and cannot be reconstructed for an existing tracked run.
- The website validates and preserves the raw evidence.
- Chosen region and observed spawn position remain separate evidence because one
  region contains many possible spawn buildings and tiles.
- Future authoritative run-data tables can index the coordinates and resolve
  them against versioned website geography without rewriting the submission.
- Deployment installs stable outpost and landmark catalogue records plus their
  Build 42.20 anchors, bounds, and raw BuildingDef mappings. A later game build
  adds a new mapping rather than changing the stable TGSRR identity.
