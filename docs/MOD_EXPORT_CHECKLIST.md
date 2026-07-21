# Mod: Export Data Checklist

## Purpose

This is the working checklist for the player/run data that TGSRR intends to collect and ultimately include in a Rat Race export. Update the status and implementation notes as collectors, persistence, integrity handling, and export serialization are completed.

TGSRR is always the sole authority for this data. Installed unrelated mods do not supply, replace, or alter any item in this checklist. The Tracker is TGSRR's player-facing presentation of the canonical state.

## Status definitions

- 🟢 **Implemented**: TGSRR already collects or persists the underlying canonical information. This does not by itself mean the final submission exporter is complete.
- 🟡 **Planned**: accepted into the export contract, with a sufficiently clear intended meaning, but collection or persistence is incomplete.
- 🔴 **Needs investigation**: desired data whose authoritative Project Zomboid event path, attribution, performance model, or precise gameplay definition must be established before implementation is promised.

## Export data

The `Contract` scope contains the agreed export contract. `Team request` contains additional desired data not already represented by a contract row.

| Scope | Data | Status | Notes |
|---|---|---|---|
| Contract | Character name | 🟢 Implemented | Starting and current character metadata are captured; the name is presentation metadata, not the run identity. |
| Contract | Starting traits | 🟡 Planned | Capture a TGSRR-owned starting snapshot using stable trait IDs; the website can use these IDs for cross-run population comparisons. |
| Contract | Current traits | 🟡 Planned | Export a current stable-ID snapshot; the website derives additions, removals, and cross-run population comparisons. |
| Contract | Run start date and time | 🟢 Implemented | Stored with the immutable TGSRR run identity. |
| Contract | Timestamp for the beginning of each survived day | 🟡 Planned | Requires the daily-history collector. |
| Contract | Total zombie kills | 🟢 Implemented | Uses the authoritative Character Info total. |
| Contract | Daily zombie-kill totals | 🟡 Planned | Requires daily baseline and rollover collection. |
| Contract | Kills with each weapon | 🟡 Planned | Requires TGSRR-owned kill attribution keyed by full item type. The website derives weapon-class totals from its item mapping unless runtime classification carries otherwise unavailable meaning. |
| Contract | Current level and XP for every skill | 🟢 Implemented | Current skill state already powers the Tracker. |
| Contract | Daily and total XP gained for every skill | 🟡 Planned | Aggregate `AddXP` by stable perk ID, seal daily values at the day boundary, and derive total XP without duplicating raw events. |
| Contract | Locations visited and when | 🟡 Planned | Requires a location registry and agreed visit semantics. |
| Contract | Towns visited and when | 🟡 Planned | Requires canonical town IDs and boundaries. |
| Contract | Books and magazines read and when | 🟡 Planned | Requires the authoritative literature-completion path. |
| Contract | Progress for every outpost | 🟢 Implemented | Latest deliverable state and observation time are persisted. |
| Contract | Completed outposts and completion order | 🟢 Implemented&nbsp;foundation | Whole-outpost completion rising-edge events and world-age timestamps exist; the final export projection will order them chronologically. |
| Contract | Kill milestones and elapsed days | 🟢 Implemented&nbsp;foundation | Persistent claims include world age; the final export projection remains to be written. |
| Contract | Skill milestones, including level 10 and elapsed days | 🟡 Planned | Generic level-reached events exist; milestone policy and persistent records remain unfinished. |
| Contract | Outpost milestones and elapsed days | 🟢 Implemented&nbsp;foundation | Deliverable and whole-outpost completion claims retain world age; the final export projection remains to be written. |
| Contract | Overall challenge progress | 🟢 Implemented | The Tracker calculates kills, skills, and outpost progress. |
| Contract | Whether the run remains official | 🟡 Planned | The classification foundation exists; final policy and transitions remain. |
| Contract | Save rollbacks, recovery decisions, and continuation as an unofficial run | 🟡 Planned | The ledger and recovery model are designed but not implemented. |
| Contract | Mods used when the run began | 🟢 Implemented | Captures Mod IDs, Workshop IDs, and their mapping. |
| Contract | Mods added or removed during later sessions | 🟢 Implemented | Session-start deltas are recorded. |
| Team request | Distance travelled | 🟡 Planned | Use compact accumulated distance rather than raw position telemetry; final rules should reject teleport/discontinuity artefacts. |
| Team request | Animals slaughtered | 🔴 Needs&nbsp;investigation | Establish authoritative action/event and species attribution. |
| Team request | Animals trapped | 🔴 Needs&nbsp;investigation | Establish the completed-trap/claim event and animal identity. |
| Team request | Animal births | 🔴 Needs&nbsp;investigation | Establish an authoritative birth event and ownership/world context. |
| Team request | XP gained through skill-book boosts | 🔴 Needs&nbsp;investigation | Define attribution when multiple XP modifiers are active and identify the authoritative multiplier state. |
| Team request | Days survived before generator knowledge is learned | 🔴 Needs&nbsp;investigation | Identify the stable knowledge/recipe ID and reliable acquisition edge. |
| Team request | Injuries sustained | 🔴 Needs&nbsp;investigation | Define injury categories and whether repeated state changes form one injury or several. |
| Team request | Zombie-caused injuries | 🔴 Needs&nbsp;investigation | Confirm reliable attacker/source attribution. |
| Team request | Milk collected | 🔴 Needs&nbsp;investigation | Trace animal/resource action completion and quantify partial collections. |
| Team request | Butter produced | 🔴 Needs&nbsp;investigation | Trace the authoritative crafting/production completion path. |
| Team request | Weapons broken | 🔴 Needs&nbsp;investigation | Confirm the reliable condition-to-broken transition and full item ID attribution. |
| Team request | Real time spent in nimble stance | 🔴 Needs&nbsp;investigation | Define stance detection, pause handling, and valid active-play accumulation. |
| Team request | Real time spent in the run/stream | 🔴 Needs&nbsp;investigation | Define active play versus pause, loading, menus, crashes, and off-stream continuation. |

## Collection principles

- Record stable in-game or TGSRR IDs rather than localized names.
- Prefer authoritative gameplay events over scans where a clean event exists.
- Aggregate high-frequency activity in memory and flush at controlled save/day/session boundaries.
- Append meaningful semantic events and checkpoints, not every sampled value change.
- Preserve world age for canonical run ordering and UTC where stream/session correlation is useful.
- Keep current-state snapshots distinct from historical timelines.
- Do not infer data that Project Zomboid cannot authoritatively expose; retain an explicit unresolved status instead.

## Export implementation reminder

Items marked **Implemented** or **Implemented foundation** indicate that their underlying canonical data exists. A separate export implementation pass must still verify that every accepted item is serialized, schema-versioned, integrity-checked, and covered by a representative test run.
