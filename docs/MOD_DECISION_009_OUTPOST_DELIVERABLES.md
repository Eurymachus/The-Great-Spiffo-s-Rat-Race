# MOD Decision 009: Outpost Deliverable Set

- Status: Accepted
- Date: 2026-07-16

## Context

The original outpost map required a secure, inhabitable church with a good bed, power, food, sealed entrances, a plumbed sink, and a spare car. The team later clarified ground-floor security requirements.

## Decision

A Completed outpost requires:

- Required room and basement activation.
- Zombie clearance across the configured `150x150` area.
- Every ground-floor exterior window barricaded at least once with wood or metal.
- Every ground-floor exterior-envelope segment fitted with a wall, window opening, or doorway containing a door.
- Every ground-floor exterior door frame contains a door and every exterior door is closed.
- At least one bed in a registered ground-floor outpost room whose vanilla `BedType` is `goodBed`.
- A connected generator at 100% fuel within the configured outpost core zone; it need not be running.
- At least 5000 calories of non-spoilable food stored in world-object containers within registered ground-floor outpost rooms. Nested containers stored within those containers count; vehicles, corpses, player inventory, and loose floor items do not.
- At least one sink in a registered ground-floor outpost room with vanilla `usesExternalWaterSource` plumbing enabled and a currently resolvable external water-source barrel. The barrel may be empty but must remain installed. Other water-piped fixtures do not qualify.
- A spare car within the outpost support area. A qualifying non-wrecked, non-trailer vehicle must have an installed driver's seat, all configured tyres installed, fuel, at least 12.5% battery charge, positive engine quality, and at least 50% engine condition. The 50% engine threshold prevents vanilla's condition-based random running stalls. A key is not required. Battery item condition, tyre condition, and tyre pressure are not checked.
- `Spare car started`: available only after the `Spare car` deliverable passes. One successful engine start from a qualifying car inside the outpost support area latches both car deliverables to that specific vehicle. They ignore ordinary condition deterioration and battery drain while it remains inside the support area, but both unlatch if that vehicle leaves, runs out of fuel, or loses its engine, fuel tank, battery, driver's seat, or any tyre. Another qualifying car can then satisfy `Spare car`, but requires its own successful start.

## Consequences

- Each requirement should expose structured current/required/status data for Outpost Overview.
- Complete is a live classification and regresses to Discovered whenever any required deliverable stops qualifying.
- Upper-floor windows and doors are outside the accepted ground-floor security scope.
- Spare-car thresholds remain mutable before release. Vehicle inspection is deliberately generic and separate from the provisional run requirement.
- Pillows do not upgrade an average or bad bed for this requirement; the fixture itself must provide vanilla Good sleep quality.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
