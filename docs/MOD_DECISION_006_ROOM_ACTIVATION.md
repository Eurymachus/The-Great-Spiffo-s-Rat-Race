# MOD Decision 006: Require Accessible Room Activation

- Status: Accepted
- Date: 2026-07-16

## Context

Indoor and basement zombies are instantiated through room discovery. Large complexes such as Hog Wallow span many basement levels, while some church towers contain decorative inaccessible RoomDefs.

## Decision

- Require every relevant accessible room and basement level in registered outpost BuildingDefs to activate.
- Use `RoomDef:isExplored()` as the Lua-visible activation proxy.
- Explicitly exclude verified inaccessible decorative RoomDefs per building.
- Do not require a room to remain physically loaded after activation.

## Consequences

- Players must traverse all relevant floors, including deep basements.
- Activation persists as evidence after chunks unload.
- Known tower exclusions are data, not a general heuristic.
- New inaccessible RoomDefs require verification and explicit exclusion until a reliable accessibility test exists.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
