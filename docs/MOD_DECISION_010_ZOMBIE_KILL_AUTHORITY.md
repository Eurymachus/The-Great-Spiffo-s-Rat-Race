# MOD Decision 010: Use the Character Zombie-Kill Counter

- Status: Accepted
- Date: 2026-07-16

## Context

The challenge win condition requires 1,000,000 zombie kills recorded in Character Info. Build 42.19's Character screen renders `IsoPlayer:getZombieKills()`, and the value is persisted with the character.

## Decision

- Use `player:getZombieKills()` as the authoritative kill value.
- Use `1,000,000` as the tracker target.
- Do not maintain a duplicate mod kill counter.
- Refresh the cached tracker record from `Events.OnZombieDead`; do not poll the player counter once per second.
- Re-read the player counter when the tracker opens or the Kills/Overview view is shown.
- Report player data as unavailable when no player object exists rather than treating it as zero.

## Consequences

- Tracker and Character Info report the same value.
- Existing game persistence supplies the current total across sessions.
- `OnZombieDead` fires after the relevant player kill-counter increment, allowing Overview and the Kills tab to observe the updated cached record immediately.
- Rates, milestones, projections, and historical deltas require separate optional state if added later.

## Related documents

- [MOD_CHALLENGE.md](MOD_CHALLENGE.md)
- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
