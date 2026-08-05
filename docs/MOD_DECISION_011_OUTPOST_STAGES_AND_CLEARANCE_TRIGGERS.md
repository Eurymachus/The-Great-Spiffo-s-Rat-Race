# MOD Decision 011: Outpost Stages and Clearance Triggers

- Status: Accepted
- Date: 2026-07-17

## Context

Earlier design used `Clearing` and `Cleared` as player-facing lifecycle stages. The tracker instead distinguishes an unknown outpost, a discovered baseline, an outpost where qualifying work has begun, and one whose complete live deliverable set passes.

## Decision

Use four player-facing stages:

- **Undiscovered**: the player has never entered the configured `150x150` clearance area.
- **Discovered**: the area has been entered, but no authoritative non-zombie deliverable has improved beyond its first-observed baseline.
- **In Progress**: at least one authoritative non-zombie deliverable has improved beyond its persisted baseline. This transition is permanently latched.
- **Complete**: room activation, zombie clearance, and every security, habitation, supplies, utilities, and vehicle requirement currently passes.

Discovery and In Progress are permanently latched. Complete is derived live and returns to In Progress if an ongoing requirement stops passing. Zombie clearance remains a structured requirement and is excluded from the In Progress transition.

During discovery, authoritative non-zombie values continuously update a draft normalized baseline while the outpost streams. Every draft change resets the settling clock. The baseline is sealed only after every non-zombie check is authoritative and the complete draft has remained unchanged for ten seconds. The outpost enters In Progress when a later normalized fraction exceeds that sealed baseline. This prevents staged room activation during TP/loading from masquerading as player work. Regressions and observational noise do not start work, and no fragile raw-world-object snapshot is required.

Evaluate clearance when:

- The player enters or loads inside an outpost clearance area.
- The player's current room changes while inside that area, allowing activation changes to be observed.
- `Events.OnZombieDead` fires while inside that area.
- A lightweight one-second fallback runs while the player remains inside that area, refreshing cached live deliverables and covering changes without a dedicated engine event.

Clearance certification cannot occur until the player has remained inside the area for ten seconds. This grace period prevents a transient empty `IsoCell:getZombieList()` during area loading from producing a false clearance result.

Clearance passes only when every required non-excluded room across all registered floors and basements is activated and `IsoCell:getZombieList()` contains no live zombie whose X/Y lies inside the clearance bounds. Z is intentionally unrestricted.

## Consequences

- `Clearing` and `Cleared` are no longer player-facing stages.
- The implementation persists discovery, per-deliverable progress baselines, a monotonic work-started latch, and an awarded clearance requirement result.
- The awarded clearance result is permanently latched and reported only as
  cleared or not cleared.
- No historical player-kill attribution is required.

## Supersedes

This decision replaces the player-facing lifecycle terminology in [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md). Its separation between zombie clearance and full completion remains valid.
