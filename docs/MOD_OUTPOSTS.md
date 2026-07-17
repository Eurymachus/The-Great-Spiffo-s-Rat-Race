# Mod: Outposts

## Player-facing role

The Rat Race requires all 13 listed church outposts to be cleared and made secure and inhabitable. Overview shows aggregate outpost completion; the Outposts tab compares locations; Outpost Overview explains one location.

Outposts may be completed in any order.

Registered outposts:

- Louisville
- Irvington
- Brandenburg
- Muldraugh
- West Point
- Rosewood
- March Ridge
- Ekron
- Riverside
- Valley Station
- Echo Creek
- Hog Wallow Military Base
- Fallas Lake

## Accepted terminology

- **Anchor**: a representative tile captured inside the mapped outpost.
- **Core zone**: the manually surveyed rectangle designating the intended outpost complex and its registered buildings.
- **Clearance area**: configured `150x150` X/Y bounds used for surrounding-zombie clearance.
- **Support radius**: provisional nearby range for support requirements such as the spare car; currently defaults to 15 tiles.
- **Activated room**: a required RoomDef whose discovery/spawn path is represented by `RoomDef:isExplored()`.
- **Undiscovered**: the player has never entered the configured clearance area.
- **Discovered**: the player has entered the clearance area, but one or more completion requirements remain.
- **Clearance**: a requirement that passes after required activation is complete and an authoritative live visit records zero zombies in the clearance area.
- **Complete**: clearance plus every required security, habitation, supplies, utilities, and vehicle deliverable currently passes.

Discovery is permanently latched. Complete is a live classification. If a required car, generator/power source, food supply, barricade, or other completion deliverable stops qualifying, the outpost returns to Discovered until the requirement is restored.

See [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md) and [MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md](MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md).

## Accepted deliverables

### Clearance and activation

- Every relevant accessible room and basement must activate.
- Inaccessible decorative RoomDefs may be explicitly excluded per registered building.
- The configured `150x150` clearance area must be cleared of zombies during an authoritative visit.

### Ground-floor security

- Every exterior window requires at least one wood or metal barricade.
- Every exterior-envelope segment must contain a wall, window opening, or doorway containing a door.
- Every exterior door frame must contain a door and every exterior door must be closed.
- These window, doorway, and exterior-wall rules apply to the ground floor only.

### Habitation, supplies, utilities, and support

- Good bed.
- Power.
- At least 5000 calories of food.
- Plumbed sink.
- Spare car near the outpost.

The original map summarizes these as `Good Bed`, `Power`, `5000+ Calories of Food`, `Sealed Entrances`, `Plumbed Sink`, and `A Spare Car`.

## Historical intent requiring specification

Earlier discussion intended the bed, food, and sink to be inside contained, sealed spaces. Exact containment and barricading rules were deferred pending team confirmation and remain unresolved.

A generator and spare car were allowed to be near the core zone rather than necessarily inside it. Current code has a provisional `supportRadius = 15`, but no accepted measurement origin or final range is documented.

## Current implementation

- `TGSRR.Outposts.add()` registration API and ordered definitions.
- One anchor, core zone, clearance center, and set of BuildingDef IDs per outpost.
- Clearance dimensions fixed to `150x150` in current definitions.
- Building and room resolution from the meta-grid.
- Room activation and floor summaries.
- Explicit decorative tower exclusions for Echo Creek, Ekron, Irvington, and Muldraugh.
- Underground BuildingDefs registered for Ekron, Hog Wallow, and Irvington.
- Provisional snapshot data: rooms, floors, buildings, and activation percentage.
- Persistent discovery and awarded-clearance records in world ModData.
- Live deliverable evaluation on area entry/load, room changes, `OnZombieDead`, and a one-second fallback while the player remains in the area.
- Normalized last-known deliverable snapshots persist for tracker display and future export when an outpost is unloaded.
- Verified ground-floor exterior-window discovery over cached building-envelope segments, one-second barricade checks, and a player-facing persisted `current / required` aggregate.

## Provisional implementation

- The clearance rectangle is centered on a configured clearance center, which may differ from the anchor. Earlier wording sometimes said "around the anchor"; current definitions are authoritative until this is explicitly resolved.
- `supportRadius = 15` exists in definitions but has no implemented requirement check.
- `RoomDef:isExplored()` is the activation proxy because `doneSpawn` has no Lua-visible getter.
- Known inaccessible rooms are excluded manually; there is no generic accessibility detector.

## Open questions

- What qualifies as a **good bed**?
- What counts as **power**, and must it currently be available?
- Which inventories count toward 5000 calories, and how are calories calculated?
- What exactly qualifies as a **plumbed sink**?
- Must bed, food, and sink be inside sealed contained spaces, and how is sealing evaluated?
- What qualifies as a **spare car**: operability, fuel, key, condition, ownership, and distance?
- Final support-radius origin and distance.
- Whether an awarded clearance requirement can later regress when zombies return.
- Final per-outpost partial-progress formula.

## Accepted Overview aggregate

Overview reports both:

- The number of currently Completed outposts out of 13.
- Overall outpost progress calculated from the sum of all individual outpost percentages divided by the maximum `1300%`.

Equivalently, the overall percentage is the arithmetic mean of the 13 individual outpost percentages. For example, three outposts at `100%` produce `3/13 completed` and approximately `23%` overall. Three outposts at `50%` produce `0/13 completed` and approximately `11.5%` overall.

The formula used to calculate each individual outpost's percentage remains unresolved.

## Related documents

- [MOD_CHALLENGE.md](MOD_CHALLENGE.md)
- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
- [MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md](MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md)
