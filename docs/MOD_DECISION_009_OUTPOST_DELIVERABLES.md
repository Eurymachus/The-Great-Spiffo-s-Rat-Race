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
- Every ground-floor exterior doorway fitted with a repaired or replaced door.
- Ground-floor exterior walls sealed.
- A good bed.
- Power.
- At least 5000 calories of food.
- A plumbed sink.
- A spare car near the outpost.

## Consequences

- Each requirement should expose structured current/required/status data for Outpost Overview.
- Completed is a live classification and regresses to Cleared whenever any required deliverable stops qualifying.
- Upper-floor windows and doors are outside the accepted ground-floor security scope.
- Exact qualification rules for bed, power, food storage, sink, door closure, sealed containment, and spare car remain open and must not be invented by implementation.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
