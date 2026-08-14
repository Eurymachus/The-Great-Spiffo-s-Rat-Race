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
- `landmarks`

Future modules may cover run information, rules, or additional milestones.
Those remain product intent rather than approved implementation scope.

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

Overview also displays an overall progress footer calculated as the arithmetic
mean of available required category percentages. Kills, Skills, and Outposts
currently participate. Optional providers are presented as cards but are
excluded from this overall figure. Landmarks are the first optional provider.

## Current UI behavior

- Fixed-size `800x650` prototype; final dimensions remain subject to in-game review.
- Contiguous tab strip beneath the title bar.
- Position, selected tab, open state, launcher position, and Outpost Overview state persist in `TGSRR/ChallengeTrackerWindow.ini`.
- Window-internal layout preferences, including collapsed Skills categories, persist in the same tracker INI state.
- Presentation actions update cached UI state and mark it dirty; they never write files directly. Dirty tracker state flushes to INI from vanilla `Events.OnSave`.
- Scrolling tracker tables permanently reserve a content gutter for their scrollbar while row backgrounds, separators, headers, and aggregate footers retain full table width.
- Movable rat-icon launcher opens and closes the tracker.
- Outpost diagnostics refresh once per second and update entries in place; Kills and Skills are event-driven through `OnZombieDead`, `AddXP`, and `LevelPerk`.
- The Landmarks tab lists 21 optional discoveries and their first-visit state.
  Its Asterisk icon/name column opens the world map through vanilla's map
  opening timed action and centers it on the location.
- Outpost Overview provides a separate map-icon button. Outpost list rows do
  not open the map; double-click retains its Outpost Overview behavior.
- The world map receives duplicate-safe red landmark Asterisks, blue outpost
  Crosses, and blue CrossedSwords for Hog Wallow Military Base.
- Tracker is player-facing for `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`; it is not debug-only.
- Player-facing tracker strings and title-case outpost names resolve through TGSRR `getTextOrNull` keys.

## Planned danger auto-close

- Add a default-enabled Mod Option that automatically closes all player-facing tracker windows when a zombie enters the same danger proximity used by vanilla Foraging/Search Mode.
- The scope includes the main Challenge Tracker and the player-facing Outpost Overview.
- Reuse the authoritative vanilla proximity rule rather than inventing a separate TGSRR radius.
- Closing for danger changes only current visibility; it must not erase saved window position, selected tab, selected outpost, or other layout preferences.
- Developer-facing Outpost survey and Inspector windows are not included unless explicitly added later.

## Outposts tab intent

The Outposts tab compares all 13 outposts. Earlier design intent included:

- A completion bar or status per outpost.
- Hover data such as last visited and last-observed zombies. The final design rejects zombie totals in favor of a binary clearance status.
- Exact remaining zombies while an authoritative clearing session is active. The final design keeps this count internal to evaluation and never displays or persists it.
- Activation and deliverable summaries.
- Activation of a row to open Outpost Overview.

The accepted player-facing stages are `Undiscovered`, `Discovered`, `In Progress`, and `Complete`. In Progress is a persisted monotonic latch triggered when an authoritative non-zombie deliverable improves beyond a discovery baseline sealed after full authority and ten unchanged seconds. `Area Cleared` remains a structured binary requirement rather than a lifecycle stage and permanently latches once awarded.

The player-facing table uses passed `Requirements`, strict `Stage`, and weighted `Progress`. Room and floor detail remains in the tooltip. Percentage semantics are defined in [MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md](MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md).

## Outpost Overview intent

Outpost Overview is the player-facing detail screen for one outpost. It should group structured deliverables such as:

- Clearance and activation.
- Ground-floor security.
- Habitation and supplies.
- Utilities.
- Support vehicle.

Rows should report structured values such as `Windows barricaded: 14/16`, not raw RoomDef IDs. The current Inspector is not this screen.

The implementation opens on double-click from the Outposts table and reports the complete persisted last-known discovery, activation, clearance, security, habitation, supplies, utilities, and vehicle deliverable set.

Persisted outpost deliverables share `available`, `passed`, `current`, `required`, optional presentation `state`, and `observedAt`. Live checks update this snapshot only when a meaningful field changes; transient debug details and world-object references are not part of the player/export contract.

Each Outpost Overview requirement row has a localized explanatory tooltip. The fixed-size window persists and clamps its screen position independently of the main tracker, remembers its open/closed state and selected outpost, and remains closed by default when no saved state exists.

`Area Cleared` is presented as a latched binary cross/check requirement. Its
question icon explains that once clearance is awarded it cannot regress, even
if zombies later return and must be dealt with again.

## Inspector responsibility

The Inspector is developer-facing diagnostics for BuildingDefs, RoomDefs, activation, loaded squares, floors, and exclusions. It remains useful through debug survey tooling but must not become the released player detail contract.

## Open questions

- Whether a future deliverable requires a documented extension beyond the accepted common fields.
- Final tracker dimensions.
- Whether a row uses a progress bar, table columns, staged status, or a combination.
- Per-outpost partial-progress formula. The aggregate formula is settled, but its inputs are not.
- Whether challenge variants share identical tracker content or receive
  submission/bounty presentation distinctions.

## Relevant implementation

- `shared/TGSRR/Challenge/TrackerRegistry.lua`
- `client/TGSRR/Tracker/Window.lua`
- `client/TGSRR/Tracker/State.lua`
- `client/TGSRR/Tracker/Overview/Module.lua`
- `client/TGSRR/Tracker/Overview/View.lua`
- `client/TGSRR/Tracker/Kills/Module.lua`
- `client/TGSRR/Tracker/Kills/Data.lua`
- `client/TGSRR/Tracker/Kills/View.lua`
  - Shows the authoritative kill total, million-kill progress, and the registered kill milestone ladder.
- `shared/TGSRR/Core/Events.lua`, `shared/TGSRR/Milestones/Registry.lua`, and `shared/TGSRR/Milestones/Ledger.lua`
  - Provide a domain-neutral event/award pipeline with persistent dynamic claim keys.
  - Definitions can be gated by challenge mode or a future option callback without changing event producers.
- `client/TGSRR/Notifications/MilestonePresenter.lua`
  - Presents awarded milestones through localized player halo text.
- `client/TGSRR/Tracker/Skills/Module.lua`
- `client/TGSRR/Tracker/Skills/Data.lua`
- `client/TGSRR/Tracker/Skills/View.lua`
- `client/TGSRR/Tracker/PendingView.lua`
- `client/TGSRR/Tracker/Outposts/Module.lua`
- `client/TGSRR/Tracker/Outposts/View.lua`
- `client/TGSRR/Tracker/Outposts/Snapshot.lua`
- `client/TGSRR/Tracker/Landmarks/Module.lua`
- `client/TGSRR/Tracker/Landmarks/View.lua`
- `client/TGSRR/Tracker/Landmarks/WorldMap.lua`
- `client/TGSRR/Run/LocationTracker.lua`

## Source organization

- `shared/TGSRR/Core`, `Challenge`, `Milestones`, and `Outposts` contain reusable definitions, registries, persistence, and calculations.
- `client/TGSRR/Tracker/<feature>` contains player-facing tracker modules and views.
- `client/TGSRR/Outposts` contains live world evaluation independent of tracker presentation.
- `client/TGSRR/Outposts/Checks` contains individual world inspection providers.
- `client/TGSRR/Outposts/Debug` contains survey, editor, and Inspector tooling that is not part of the player-facing contract.
- `client/LastStand` remains in the engine-prescribed challenge location.

## Related documents

- [MOD_NOW.md](MOD_NOW.md)
- [MOD_CHALLENGE.md](MOD_CHALLENGE.md)
- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_TECHNICAL_CONSTRAINTS.md](MOD_TECHNICAL_CONSTRAINTS.md)
- [MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md](MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md)
- [MOD_DECISION_009_OUTPOST_DELIVERABLES.md](MOD_DECISION_009_OUTPOST_DELIVERABLES.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
