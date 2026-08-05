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
- **Discovered**: the player has entered the clearance area, but no authoritative non-zombie deliverable has improved beyond its settled discovery baseline.
- **In Progress**: at least one non-zombie deliverable has improved beyond its persisted baseline.
- **Clearance**: a requirement that passes after required activation is complete and an authoritative live visit records zero zombies in the clearance area.
- **Complete**: clearance plus every required security, habitation, supplies, utilities, and vehicle deliverable currently passes.

Discovery and In Progress are permanently latched. Complete is a live classification. If a required car, generator, food supply, barricade, or other completion deliverable stops qualifying, the outpost returns to In Progress until the requirement is restored.

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

- At least one bed in a registered ground-floor outpost room whose vanilla `BedType` is `goodBed` and therefore provides Good sleep quality. Pillows do not upgrade another bed type for this deliverable.
- A generator placed within the configured core zone, connected, and at 100% fuel. It need not be running or actively supplying electricity.
- At least 5000 calories of non-spoilable food stored in world-object containers within registered ground-floor rooms. Food inside nested bags counts; vehicles, corpses, player inventory, and loose floor items do not.
- At least one sink in a registered ground-floor room plumbed to a currently installed external water-source barrel using vanilla plumbing. The barrel may be empty but must remain resolvable by `FindExternalWaterSource()`. Toilets, showers, baths, and dishwashers do not qualify.
- Spare car within the support area. The current provisional rule requires 75% engine condition, fuel, battery condition and charge, driver-seat condition, and condition and inflation for every script-defined tyre.

The original map summarizes these as `Good Bed`, `Power`, `5000+ Calories of Food`, `Sealed Entrances`, `Plumbed Sink`, and `A Spare Car`.

## Historical intent requiring specification

Earlier discussion intended the bed, food, and sink to be inside contained, sealed spaces. Exact containment and barricading rules were deferred pending team confirmation and remain unresolved.

A spare car is allowed within the core zone or within the provisional `supportRadius = 15` measured from the nearest edge of that zone.

## Current implementation

- `TGSRR.Outposts.add()` registration API and ordered definitions.
- One anchor, core zone, clearance center, and set of BuildingDef IDs per outpost.
- Clearance dimensions fixed to `150x150` in current definitions.
- Building and room resolution from the meta-grid.
- Room activation and floor summaries.
- Explicit decorative tower exclusions for Echo Creek, Ekron, Irvington, and Muldraugh.
- Underground BuildingDefs registered for Ekron, Hog Wallow, and Irvington.
- Player-facing snapshot data: rooms, weighted progress, strict stage, and persisted deliverable records.
- Player-facing `Area Cleared` uses only a latched cross/check state plus an
  explanatory question-icon tooltip. Zombie totals are not displayed.
- Outpost Overview has a dedicated map button that queues vanilla's world-map
  opening timed action and centers at the outpost anchor. The world map carries
  a blue Cross for ordinary outposts and blue CrossedSwords for Hog Wallow.
- Persistent discovery and awarded-clearance records in world ModData.
- Live deliverable evaluation on area entry/load, room changes, `OnZombieDead`, and a one-second fallback while the player remains in the area.
- Normalized last-known deliverable snapshots persist for tracker display and future export when an outpost is unloaded.
- Verified ground-floor exterior-window discovery over cached building-envelope segments, one-second barricade checks, and a player-facing persisted `current / required` aggregate.
- A two-way RoomDef/outpost index routes `OnObjectAdded` and `OnObjectAboutToBeRemoved` changes for vanilla `BedType == "goodBed"` fixtures.
- Good-bed installation entries persist by outpost, coordinates, and sprite-derived key. The saved ledger is authoritative across sessions; challenge fixtures are not discovered through object scans.
- Loaded generators are reconciled once per second from `IsoCell:getProcessIsoObjects()`, because generator placement does not reliably raise `OnObjectAdded`. A generator inside the core zone persists by XYZ and sprite-derived key; the recorded generator is then resolved directly and checked for connection and fuel percentage.
- Food containers are discovered after all registered ground-floor room squares are streamed, then maintained from object-add/remove events. Only those cached container contents are totalled once per second while the outpost is active. Streaming loss invalidates the object-reference cache without overwriting the last persisted result; the cache and live result are rebuilt when the rooms stream again.
- Sink candidates share the streamed room-object cache and are maintained through the same object-add/remove events. Their live plumbing latch and `FindExternalWaterSource()` result are checked once per second while the outpost is active, so removing the barrel regresses the requirement and replacing it restores the pass without replumbing.
- Sink presentation distinguishes `None`, `Not Plumbed`, `Water Source Missing`, and `Connected`; only `Connected` passes.

## Provisional implementation

- The clearance rectangle is centered on a configured clearance center, which may differ from the anchor. Earlier wording sometimes said "around the anchor"; current definitions are authoritative until this is explicitly resolved.
- `supportRadius = 15` is implemented for spare-car discovery but remains provisional pending release review.
- `RoomDef:isExplored()` is the activation proxy because `doneSpawn` has no Lua-visible getter.
- Known inaccessible rooms are excluded manually; there is no generic accessibility detector.

## Open questions

- Must bed, food, and sink be inside a more narrowly defined sealed contained space than the registered ground-floor outpost rooms, and how is that containment evaluated?
- Whether the provisional **spare car** thresholds, support radius, and omission of a key requirement are correct for release.
- Final support-radius origin and distance.
- Awarded zombie clearance is permanently latched and cannot regress when zombies return.
- Final per-outpost partial-progress formula.

## Accepted Overview aggregate

Overview reports both:

- The number of currently Completed outposts out of 13.
- Overall outpost progress calculated from the sum of all individual outpost percentages divided by the maximum `1300%`.

Equivalently, the overall percentage is the arithmetic mean of the 13 individual outpost percentages. For example, three outposts at `100%` produce `3/13 completed` and approximately `23%` overall. Three outposts at `50%` produce `0/13 completed` and approximately `11.5%` overall.

Each individual percentage uses the accepted weighted deliverable formula in [MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md](MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md). Completion remains a strict all-deliverables pass and cannot be obtained from percentage rounding.

## Related documents

- [MOD_CHALLENGE.md](MOD_CHALLENGE.md)
- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
- [MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md](MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md)
