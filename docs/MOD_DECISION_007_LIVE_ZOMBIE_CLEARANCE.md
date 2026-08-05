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
- Persist only the binary cleared or not-cleared state for reporting and export.
- Permanently latch the cleared state once awarded.

## Consequences

- Live in-zone counts are exact for instantiated zombies.
- Live counts are an evaluation input only and are not exposed or persisted.
- Debug radar, reflection, forced loading, and renderer parsing are rejected for released certification.
- Returning zombies cannot revoke an awarded clearance result.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
