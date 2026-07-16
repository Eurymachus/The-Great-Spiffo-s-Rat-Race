# MOD Decision 005: Use Explicit Core, Clearance, and Support Areas

- Status: Accepted
- Date: 2026-07-16

## Context

Outposts may span multiple connected structures and deep basement BuildingDefs. BuildingDef rectangles and vanilla animal zones do not directly express all challenge semantics.

## Decision

Represent each outpost with separate spatial concepts:

- An anchor identifies a representative mapped tile.
- A manually surveyed core zone designates the intended complex and registered BuildingDefs.
- A configured `150x150` clearance area defines surrounding-zombie clearance in X/Y across all levels.
- Nearby support requirements use a separate support range rather than requiring the object inside a building.

Use `TGSRR.Outposts.add()` and declarative definitions so checks and UI do not hard-code each location.

## Consequences

- Multi-building and underground complexes are supported.
- Generator/power and spare-car checks may look near the core rather than only inside rooms.
- The current clearance center may differ from the anchor; earlier "around the anchor" wording is not silently substituted for current definitions.
- The current 15-tile support radius is provisional pending a final origin and range decision.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
