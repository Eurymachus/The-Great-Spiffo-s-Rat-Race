# MOD Decision 007: Certify Zombie Clearance During a Live Visit

- Status: Accepted
- Date: 2026-07-16

## Context

Normal Lua cannot query the native virtual-zombie population in arbitrary unloaded areas. Debug radar and reflection are not available to end users. The game already maintains instantiated zombies in `IsoCell:getZombieList()`.

## Decision

During an active outpost visit:

- Monitor `IsoCell:getZombieList()` rather than scanning every square.
- Count zombies whose X/Y lies inside the configured `150x150` clearance bounds; Z is intentionally irrelevant.
- Require room activation before awarding clearance.
- Record the result when the authoritative live count reaches zero.
- Persist cleared state and last-observed data for player-facing reporting after the area unloads.

## Consequences

- Live in-zone counts are exact for instantiated zombies.
- Remote values are historical observations, not fresh native-population queries.
- Debug radar, reflection, forced loading, and renderer parsing are rejected for released certification.
- Session start/resume rules, persistence location, migration handling, and regression policy still require implementation detail.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
