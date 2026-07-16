# Mod: Current Focus

## Branch and worktree

- Development branch: `codex/outpost-tracker-dev`.
- Live challenge branch: `master`.
- Project Zomboid loads the main mod worktree. Switch to `master` for an active run and back to the development branch for tracker work.
- Current tracker and documentation changes are uncommitted.

## Current deliverable

Build a modular, player-facing Rat Race Challenge Tracker with:

- An **Overview** tab for aggregate challenge deliverables.
- Dedicated system tabs, beginning with **Outposts**.
- A stable boundary between provisional diagnostics and final deliverables.
- A player-facing Outpost Overview distinct from the debug Inspector.

See [MOD_CHALLENGE.md](MOD_CHALLENGE.md), [MOD_TRACKER.md](MOD_TRACKER.md), and [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md).

## Implemented on the development branch

- Generic `TGSRR.ChallengeTracker.registerModule()` registry.
- Overview, Kills, Skills, and Outposts modules in a fixed-size `800x650` tabbed window.
- Generic `ChallengeDeliverables` provider registry and normalized Overview record boundary.
- Overview summaries for Outposts, Skills, and Zombie Kills; unavailable systems are labelled rather than inferred.
- Event-driven Kills deliverable and detail tab using `OnZombieDead` and the persisted Character Info zombie-kill counter with a `1,000,000` target.
- Saved window position, selected tab, open state, and movable launcher position.
- Movable `Item_DeadRat.png` launcher with runtime outline and no button chrome.
- One-second refresh that updates stable list entries in place.
- Provisional Outposts percentage derived from the arithmetic mean of the 13 room-activation percentages.
- Outpost registration API, 13 definitions, configured core zones, `150x150` clearance bounds, registered BuildingDefs, and manual inaccessible-room exclusions.
- Room activation via `RoomDef:isExplored()` and loaded-square diagnostics.
- Debug survey, zone editor, teleport controls, and activation Inspector.
- Respawn removal for all Rat Race challenge variants.

## Provisional implementation

- Tracker dimensions are `800x650`; final size remains open to in-game review.
- Outposts completion count is unavailable until final completion checks exist; Overview displays `- / 13` rather than claiming zero.
- Outposts columns (`Rooms`, `Floors`, `Buildings`, `%`) are diagnostics, not final deliverables.
- Double-click opens the debug Inspector as a placeholder for Outpost Overview.
- Tracker launches for official, CDDA, and Sprinters variants; submission/bounty presentation differences are not implemented.

## Not implemented

- Live outpost clearing sessions and persistent cleared/completed state.
- Zombie count, last visited, or last-observed population in tracker snapshots.
- Security, habitation, supplies, utilities, and vehicle checks.
- Skill-set verification; its tab currently contains an explicit pending-state view.
- Final per-outpost partial-progress formula.

## Recommended next action

Implement the persistent runtime outpost state model (`Unvisited`, `Discovered`, `Clearing`, `Cleared`, `Completed`). Cleared-state regression is deferred; do not encode a permanent or regressive policy yet.

## Related decisions

- [MOD_DECISION_001_TRACKER_ARCHITECTURE.md](MOD_DECISION_001_TRACKER_ARCHITECTURE.md)
- [MOD_DECISION_002_OVERVIEW_DELIVERABLES.md](MOD_DECISION_002_OVERVIEW_DELIVERABLES.md)
- [MOD_DECISION_003_CHALLENGE_CONTRACT.md](MOD_DECISION_003_CHALLENGE_CONTRACT.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
- [MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md](MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
- [MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md](MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
