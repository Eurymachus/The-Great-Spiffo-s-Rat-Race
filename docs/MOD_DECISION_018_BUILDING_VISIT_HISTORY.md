# MOD Decision 018: Persist Physical Building Visits

- Status: Accepted
- Date: 2026-08-04

## Context

Future Rat Race revisions may add a landmark or another visit requirement after
a run has already entered the relevant building. Requiring another visit would
discard evidence that TGSRR could have retained cheaply.

Vanilla persists `RoomDef.explored`, but that state is not an authoritative
record that the player entered a building. Seeing a room can mark it explored,
and `IsoRoom:onSee()` can update other eligible rooms in the same building.
`StashSystem.visitedBuilding()` is stash-specific bookkeeping rather than a
general visit history.

## Decision

TGSRR maintains a run-scoped `buildingVisits` set keyed by the precision-safe
string returned by `BuildingDef:getIDString()`.

A visit is recorded only when the player's current square resolves through
`IsoGridSquare:getBuilding()` to that BuildingDef. Merely seeing through a
window, revealing a room, or entering a surrounding coordinate zone does not
count.

Only the first physical entry is retained. Its record contains:

- Real UTC timestamp.
- World age in hours.
- In-game year, month, day, and time of day.
- Entry X, Y, and Z coordinates.

The existing one-second location observation performs the check. Remaining in
the same building is short-circuited before the persistent table lookup.

`LocationTracker.hasVisitedBuilding(buildingId)` and
`LocationTracker.getBuildingVisit(buildingId)` provide the reconciliation
boundary for future registries.

The registry is internal run ModData. It is deliberately excluded from the
event ledger and export contract. Registered landmarks continue to create
their existing `location.visited` event and exported visit projection.

Runs whose tracking began before the registry existed are marked with
`buildingVisitsPartial = true`. Fresh runs have complete history from tracker
initialization onward.

## Consequences

- A future building-based requirement can reconcile a prior physical visit
  without asking the player to return.
- Storage and runtime cost grow only with unique buildings entered.
- Vanilla room exploration is not used as substitute evidence.
- Building IDs remain map-definition identifiers. A map revision that replaces
  a BuildingDef may require an explicit migration or coordinate-based mapping.

## Related documents

- [MOD_RUN_DATA.md](MOD_RUN_DATA.md)
- [MOD_GAMEPLAY_SYSTEMS.md](MOD_GAMEPLAY_SYSTEMS.md)
- [MOD_TRACKER.md](MOD_TRACKER.md)
