# MOD Decision 011: Simplify Outpost Stages and Clearance Triggers

- Status: Accepted
- Date: 2026-07-17

## Context

Earlier design used `Clearing` and `Cleared` as player-facing lifecycle stages. The tracker only needs to distinguish an unknown outpost, a known unfinished outpost, and one whose complete live deliverable set passes.

## Decision

Use three player-facing stages:

- **Undiscovered**: the player has never entered the configured `150x150` clearance area.
- **Discovered**: the area has been entered, but one or more completion requirements do not pass.
- **Complete**: room activation, zombie clearance, and every security, habitation, supplies, utilities, and vehicle requirement currently passes.

Discovery is permanently latched. Complete is derived live and returns to Discovered if an ongoing requirement stops passing. Zombie clearance remains a structured requirement rather than a player-facing stage.

Evaluate clearance when:

- The player enters or loads inside an outpost clearance area.
- The player's current room changes while inside that area, allowing activation changes to be observed.
- `Events.OnZombieDead` fires while inside that area.
- A lightweight one-second fallback runs while the player remains inside that area, refreshing cached live deliverables and covering changes without a dedicated engine event.

Clearance certification cannot occur until the player has remained inside the area for ten seconds. This grace period prevents a transient empty `IsoCell:getZombieList()` during area loading from producing a false clearance result.

Clearance passes only when every required non-excluded room across all registered floors and basements is activated and `IsoCell:getZombieList()` contains no live zombie whose X/Y lies inside the clearance bounds. Z is intentionally unrestricted.

## Consequences

- `Clearing` and `Cleared` are no longer player-facing stages.
- The implementation persists discovery and an awarded clearance requirement result.
- The clearance-regression policy remains deferred; the current awarded result is latched until that policy is settled.
- No historical player-kill attribution is required.

## Supersedes

This decision replaces the player-facing lifecycle terminology in [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md). Its separation between zombie clearance and full completion remains valid.
