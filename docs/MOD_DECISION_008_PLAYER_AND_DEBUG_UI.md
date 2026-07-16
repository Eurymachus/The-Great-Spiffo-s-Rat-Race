# MOD Decision 008: Separate Player UI from Debug Survey Tools

- Status: Accepted
- Date: 2026-07-16

## Context

The survey and Inspector were created to discover BuildingDefs, zones, floors, activation, and exclusions. The released tracker needs stable challenge language rather than internal IDs and diagnostics.

## Decision

- Challenge Tracker, Overview, Outposts tab, and Outpost Overview are player-facing.
- Survey window, teleport controls, zone editor, and activation Inspector are developer/debug tooling.
- Clicking an outpost in the released tracker should open Outpost Overview, not the debug Inspector.
- Player-facing rows use structured deliverables such as `Windows barricaded: 14/16`; debug views may show BuildingDef and RoomDef details.

## Consequences

- The current double-click path to Inspector is explicitly a provisional placeholder.
- Debug tools may continue to support definition maintenance without defining the released UI contract.
- The final Outpost Overview must be implemented before release.

## Related documents

- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_001_TRACKER_ARCHITECTURE.md](MOD_DECISION_001_TRACKER_ARCHITECTURE.md)
