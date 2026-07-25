# Mod: Current Focus

## Branch and worktree

- Development branch: `codex/outpost-tracker-dev`.
- Live challenge branch: `master`.
- Project Zomboid loads the main mod worktree. Switch to `master` for an active run and back to the development branch for tracker work.
- The modular tracker baseline is committed at `737331b`.

## Current deliverable

Build a modular, player-facing Rat Race Challenge Tracker with:

- An **Overview** tab for aggregate challenge deliverables.
- Dedicated system tabs, beginning with **Outposts**.
- A stable boundary between provisional diagnostics and final deliverables.
- A player-facing Outpost Overview distinct from the debug Inspector.

See [MOD_CHALLENGE.md](MOD_CHALLENGE.md), [MOD_TRACKER.md](MOD_TRACKER.md), [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md), [MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md](MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md), and [MOD_DECISION_015_SOURCE_LAYOUT.md](MOD_DECISION_015_SOURCE_LAYOUT.md).

Run-history and TGSRR-owned collection design is documented in [MOD_RUN_DATA.md](MOD_RUN_DATA.md), with implementation status maintained in [MOD_EXPORT_CHECKLIST.md](MOD_EXPORT_CHECKLIST.md). Techniques audited from unrelated mods are retained strictly as implementation research in [MOD_REFERENCE_DATA_COLLECTORS.md](MOD_REFERENCE_DATA_COLLECTORS.md).

## Implemented on the development branch

- Generic `TGSRR.ChallengeTracker.registerModule()` registry.
- Overview, Kills, Skills, and Outposts modules in a fixed-size `800x650` tabbed window.
- Generic `ChallengeDeliverables` provider registry and normalized Overview record boundary.
- Overview summaries for Outposts, Skills, and Kills.
- Event-driven Kills deliverable and detail tab using `OnZombieDead` and the persisted Character Info zombie-kill counter with a `1,000,000` target.
- Generic challenge event bus, persistent milestone ledger, registry-driven awards, and localized halo notification presenter.
- Kill milestones at 1,000, 10,000, 25,000, 50,000, 100,000, 250,000, 500,000, 750,000, and 1,000,000, shown on the Kills tab and emitted only when thresholds are crossed.
- Dynamic all-skills level-10 deliverable grouped by vanilla skill category, with ten-segment per-skill progress, aggregate fractional progress, and event-driven refresh.
- World-scoped Rat Race run identity foundation with immutable `runId`, starting-character metadata, versioned `run.meta`, and timestamped session/mod-list history.
- Canonical schema-1 event codec, SHA-256 hash-chained ledger, append-safe segmented storage, lifecycle verification, and migration support for pre-release test ledgers.
- TGSRR-owned daily history with UTC/world-age day boundaries, daily kill deltas, and non-zero per-skill XP deltas.
- TGSRR-owned weapon-kill attribution keyed by full item type or explicit
  non-item pseudo ID, with cumulative totals, completed-day deltas, active-day
  deltas, and partial-baseline disclosure for existing runs.
- Separate cumulative, completed-day, and active-day zombie fire-death counts
  that never contribute to vanilla or weapon-kill totals.
- Permanent first-visit tracking for 12 canonical towns using stable TGSRR IDs,
  map-reviewed multi-point coverage with per-point radii, hash-chained
  `town.visited` events, and partial-history disclosure for migrated runs.
- Immutable literature read-state baseline plus hash-chained successful-reading
  deltas from PZ's authoritative `ISReadABook.complete()` edge. Current export
  derives full item, literature-title, and print-media sets without mistaking
  profession knowledge for physical reading.
- Versioned non-town location registry, lightweight first-visit collector, and
  schema-1 export projection. Registry version 0 intentionally contains no
  definitions while the canonical location list is deferred.
- Compact loaded-mod history: a complete initial Mod ID/Workshop ID baseline followed by timestamped added, removed, and changed-association session deltas.
- Versioned, deterministic LZSS/Base64URL run exports containing the complete verified event history, integrity metadata, and a live current-kills projection.
- Pre-spawn capture of the raw namespaced trait IDs selected on the character-creation screen, persisted across the loading transition and consumed only by the matching new character.
- Format-3 current-state projection containing challenge mode; character and trait state; current skills; all 13 current outposts; all 12 town-visit states; versioned non-town location state; literature baseline/current/completion state; rules-versioned Tracker summaries; current active mods; and a non-mutating active-day snapshot with live kill and per-skill XP deltas.
- Cooperative pause-menu export flow with progress presentation, read-back verification, explicit clipboard copy, and format-1 export compatibility.
- Generic `skill.level.reached` events containing the skill, parent category, and reached level; award policy remains intentionally undecided.
- Rising-edge events for individual outpost deliverable completion and whole-outpost completion; initial observations do not retroactively award milestones.
- Saved window position, selected tab, open state, and movable launcher position.
- Movable `Item_DeadRat.png` launcher with runtime outline and no button chrome.
- One-second refresh that updates stable list entries in place.
- Weighted Outposts percentage derived from the arithmetic mean of the 13 weighted individual percentages.
- Outpost registration API, 13 definitions, configured core zones, `150x150` clearance bounds, registered BuildingDefs, and manual inaccessible-room exclusions.
- Room activation via `RoomDef:isExplored()` and loaded-square diagnostics.
- Persistent outpost discovery when the player enters a configured `150x150` clearance area.
- Weighted per-outpost progress across all 13 deliverables, strict Complete derivation, Completed / 13 Overview count, and arithmetic-mean aggregate progress.
- Persisted per-deliverable discovery baselines and a monotonic `In Progress` stage triggered by non-zombie improvement.
- Live outpost evaluation on area entry/load, room changes, zombie deaths, and a one-second in-area fallback.
- Disposable-schema `shared/TGSRR/Outposts/ProgressStore` with normalized, change-only persistent deliverable snapshots.
- Cached exterior-envelope geometry followed by lightweight one-second window/barricade checks.
- Persistent room activation, floor activation, zombie clearance, window-barricade, enclosure, fitted-door, closed-door, and good-bed records.
- Registered-room reverse lookup routes good-bed object additions/removals to one outpost and maintains a persistent fixture ledger without scanning for challenge fixtures.
- Deliverable-ledger changes notify open tracker views immediately; their one-second refresh remains a presentation fallback.
- Debug survey, zone editor, teleport controls, and activation Inspector.
- Debug survey of loaded ground-floor exterior windows, frames, player-built windows, and barricades.
- Respawn removal for all Rat Race challenge variants.

## Provisional implementation

- Tracker dimensions are `800x650`; final size remains open to in-game review.
- Outposts columns are passed `Requirements`, strict `Stage`, and weighted `Progress`; room and floor detail remains available in the tooltip.
- Tracker-owned player-facing strings and all 13 title-case outpost names use TGSRR `getTextOrNull` translation keys.
- Outpost rows use vanilla's tintable `Cross` world-map symbol as a consistent church marker.
- Hog Wallow Military Base uses vanilla's tintable `CrossedSwords` map marker.
- Double-clicking an outpost opens the localized player-facing Outpost Overview with the full persisted deliverable set.
- The player-facing Outpost Overview displays all current completion checks and last-known persisted values.
- Outpost Overview rows provide localized requirement tooltips, and the window remembers its screen position, open/closed state, and selected outpost.
- Tracker launches for official, CDDA, and Sprinters variants; submission/bounty presentation differences are not implemented.

## Not implemented

- Zombie count, last visited, or last-observed population in tracker snapshots.
- Skill milestone award selection (individual skills, categories, or selected levels).
- Default-enabled danger auto-close for the Challenge Tracker and Outpost Overview using vanilla Foraging/Search Mode zombie proximity.

## Recommended next action

Define the canonical non-town location membership when ready, or continue with
future eligibility classification.

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
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
- [MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md](MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md)
- [MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md](MOD_DECISION_013_OUTPOST_PROGRESS_WEIGHTS.md)
- [MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md](MOD_DECISION_014_CHALLENGE_EVENTS_AND_MILESTONES.md)
- [MOD_DECISION_015_SOURCE_LAYOUT.md](MOD_DECISION_015_SOURCE_LAYOUT.md)
- [MOD_DECISION_016_SKILL_TRACKING.md](MOD_DECISION_016_SKILL_TRACKING.md)
- [MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md](MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md)
