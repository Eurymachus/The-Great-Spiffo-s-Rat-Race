# MOD Decision 004: Separate Outpost Clearing from Completion

- Status: Superseded in part by Decision 011
- Date: 2026-07-16

## Context

Killing surrounding zombies and making a church secure and inhabitable are related but distinct pieces of the outpost objective.

## Decision

Use distinct lifecycle semantics:

- **Approaching/Proximity**: informational UI when a player nears an outpost; not certification.
- **Clearing**: an authoritative visit is actively monitoring activation and zombies.
- **Cleared**: all required accessible rooms/floors have activated and the live zombie count inside the configured clearance area reaches zero.
- **Completed**: Cleared plus every security, habitation, supplies, utilities, and vehicle requirement currently passes.

The cleared result is recorded from the authoritative visit rather than reconstructed remotely after unloading.

Completed is not permanently latched. If a required car, generator/power source, food supply, barricade, or other completion requirement stops qualifying, the outpost regresses to Cleared until every requirement passes again.

## Consequences

- The tracker exposes only the binary zombie-clearance status, never a live or last-observed zombie total.
- Outposts may be cleared and completed in any order.
- `Cleared` must not be used as a synonym for `Completed`.
- Completion checks can be modular and independently report current/required values.
- Zombie clearance is permanently latched once awarded. Full outpost completion may still regress when another ongoing requirement stops passing.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
