# Mod: Challenge Tracker

## Purpose

The Challenge Tracker is the player-facing summary of a long-form ironman Rat Race run. It should make an extreme challenge legible without changing its rules or replacing the tension of discovering and clearing the world.

## Accepted information hierarchy

1. **Overview** answers: "How is the challenge going?"
2. **System tabs** answer: "What contributes to this deliverable?"
3. **Record detail views** answer: "Why does this specific record pass or fail?"

Overview shows one aggregate record per challenge deliverable. It does not repeat every outpost. See [MOD_DECISION_001_TRACKER_ARCHITECTURE.md](MOD_DECISION_001_TRACKER_ARCHITECTURE.md) and [MOD_DECISION_002_OVERVIEW_DELIVERABLES.md](MOD_DECISION_002_OVERVIEW_DELIVERABLES.md).

## Accepted module contract

Modules register through `TGSRR.ChallengeTracker.registerModule()` with an ID, title, order, and view factory. The shell owns tabs and persistence; each module owns its view and refresh behavior.

Current modules:

- `overview`
- `kills`
- `skills`
- `outposts`

Future modules may cover skills, kills, run information, rules, or milestones. Those were discussed as product intent, not approved implementation scope.

## Deliverable boundary

Overview consumes generic player-facing records from `TGSRR.ChallengeDeliverables`, rather than inspection structures. Providers register an ID, label, order, and `getRecord(context)` function. Normalized records currently use this approximate shape:

```lua
{
    id = "outposts",
    label = "Outposts",
    current = 3,
    target = 13,
    percent = 23,
    status = "in_progress",
}
```

The schema supports counts, percentages, availability, status, explanatory detail, and navigation without exposing debug checks. It may be extended as final systems are implemented.

For the outposts record, `current` is the number of currently Completed outposts, `target` is 13, and `percent` is the arithmetic mean of the 13 individual outpost percentages. The percentage therefore includes partial outpost progress even when `current` remains zero.

## Current UI behavior

- Fixed-size `800x650` prototype; final dimensions remain subject to in-game review.
- Contiguous tab strip beneath the title bar.
- Position, selected tab, open state, and launcher position persist in `TGSRR/ChallengeTrackerWindow.ini`.
- Movable rat-icon launcher opens and closes the tracker.
- Outpost diagnostics refresh once per second and update entries in place; Kills is event-driven through `OnZombieDead`.
- Tracker is player-facing for `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`; it is not debug-only.
- Player-facing tracker strings and title-case outpost names resolve through TGSRR `getTextOrNull` keys.

## Outposts tab intent

The Outposts tab compares all 13 outposts. Earlier design intent included:

- A completion bar or status per outpost.
- Hover data such as last visited and last-observed zombies.
- Exact remaining zombies while an authoritative clearing session is active.
- Activation and deliverable summaries.
- Activation of a row to open Outpost Overview.

The accepted player-facing stages are `Undiscovered`, `Discovered`, and `Complete`. Clearance and remaining zombies are structured requirement details within the Discovered stage rather than separate lifecycle stages.

The current diagnostic table is provisional. Final columns and percentage semantics remain open.

## Outpost Overview intent

Outpost Overview is the player-facing detail screen for one outpost. It should group structured deliverables such as:

- Clearance and activation.
- Ground-floor security.
- Habitation and supplies.
- Utilities.
- Support vehicle.

Rows should report structured values such as `Windows barricaded: 14/16`, not raw RoomDef IDs. The current Inspector is not this screen.

The implementation opens on double-click from the Outposts table and reports persisted last-known discovery, activation, clearance, and window-barricade results. Remaining security, habitation, supplies, utilities, and vehicle rows explicitly show Unavailable until their qualification rules are implemented.

Persisted outpost deliverables share `available`, `passed`, `current`, `required`, and `observedAt`. Live checks update this snapshot only when a meaningful field changes; transient debug details and world-object references are not part of the player/export contract.

Each Outpost Overview requirement row has a localized explanatory tooltip. The fixed-size window persists and clamps its screen position independently of the main tracker.

## Inspector responsibility

The Inspector is developer-facing diagnostics for BuildingDefs, RoomDefs, activation, loaded squares, floors, and exclusions. It remains useful through debug survey tooling but must not become the released player detail contract.

## Open questions

- Whether a future deliverable requires a documented extension beyond the accepted common fields.
- Final tracker dimensions.
- Whether a row uses a progress bar, table columns, staged status, or a combination.
- Per-outpost partial-progress formula. The aggregate formula is settled, but its inputs are not.
- Whether unofficial variants share identical tracker content or receive submission/bounty distinctions.

## Relevant implementation

- `ChallengeTracker.lua`
- `ChallengeTrackerWindow.lua`
- `ChallengeTrackerState.lua`
- `OverviewTrackerModule.lua`
- `OverviewTrackerView.lua`
- `KillsTrackerModule.lua`
- `KillsTrackerData.lua`
- `KillsTrackerView.lua`
- `SkillsTrackerModule.lua`
- `PendingTrackerView.lua`
- `OutpostTrackerModule.lua`
- `OutpostTrackerView.lua`
- `OutpostTrackerSnapshot.lua`

## Related documents

- [MOD_NOW.md](MOD_NOW.md)
- [MOD_CHALLENGE.md](MOD_CHALLENGE.md)
- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md](MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
