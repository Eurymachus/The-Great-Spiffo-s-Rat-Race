# Mod: Export Data Checklist

## Purpose

This is the working checklist for the player/run data that TGSRR intends to collect and ultimately include in a Rat Race export. Update the status and implementation notes as collectors, persistence, integrity handling, and export serialization are completed.

TGSRR is always the sole authority for this data. Installed unrelated mods do not supply, replace, or alter any item in this checklist. The Tracker is TGSRR's player-facing presentation of the canonical state.

## Status definitions

- 🟢 **Implemented**: TGSRR already collects or persists the underlying canonical information. This does not by itself mean the final submission exporter is complete.
- 🔵 **In progress — awaiting decision**: the technical collection/export
  infrastructure exists, but an agreed content or policy decision is still
  required before the contract can be activated and considered complete.
- 🟡 **Planned**: accepted into the export contract, with a sufficiently clear intended meaning, but collection or persistence is incomplete.
- 🔴 **Needs investigation**: desired data whose authoritative Project Zomboid event path, attribution, performance model, or precise gameplay definition must be established before implementation is promised.

## Export data

The `Contract` scope contains the agreed export contract. `Team request` contains additional desired data not already represented by a contract row.

| Scope | Data | Status | Notes |
|---|---|---|---|
| Contract | Character name | 🟢 Implemented | Starting and current character metadata are captured; the name is presentation metadata, not the run identity. |
| Contract | Starting traits | 🟢 Implemented | Raw namespaced trait IDs are captured from the selected-traits list before the character-creation transition and persisted immutably for the matching new character. Migrated or missed captures are explicitly marked partial. Spawned effective traits are retained separately. |
| Contract | Current traits | 🟢 Implemented | Format-3 exports contain the current sorted effective trait-ID set; the website derives additions, removals, and cross-run population comparisons. |
| Contract | Run start date and time | 🟢 Implemented | Stored with the immutable TGSRR run identity. |
| Contract | Timestamp for the beginning of each survived day | 🟢 Implemented | A hash-chained `day.started` event records UTC, world age, calendar date, and the survived-day index. The first observation is marked partial when an existing run is bootstrapped. |
| Contract | Total zombie kills | 🟢 Implemented | Uses the authoritative Character Info total. |
| Contract | Daily zombie-kill totals | 🟢 Implemented | Each `day.started` event seals the preceding day's delta from authoritative Character Info kill totals. Format-3 also exports the active unfinished day's live delta without mutating history. |
| Contract | Kills with each weapon | 🟢 Implemented | TGSRR attributes player-credited deaths using the actual hit weapon and credited attacker. Format-3 exports cumulative ID-sorted totals and active-day deltas keyed by full item type or `__VEHICLE__`, `__UNARMED__`, and `__UNKNOWN__`. Vanilla does not credit delayed fire deaths to the player. Existing runs disclose a partial baseline. |
| Team request | Zombies killed by fire | 🟢 Implemented | Tracked separately from vanilla and weapon kills because ongoing fire clears `attackedBy` and does not increment player kills. Format-3 exports cumulative and active-day fire-death counts with partial-baseline disclosure. |
| Contract | Current level and XP for every skill | 🟢 Implemented | Format-3 exports every registered non-category perk as a stable, ID-sorted record containing category ID, current level, and cumulative XP. Localized names are intentionally excluded. |
| Contract | Daily and total XP gained for every skill | 🟢 Implemented | Day-boundary snapshots use stable perk IDs and seal non-zero XP deltas for the preceding day. Format-3 includes the active unfinished day's non-zero deltas, while total gain remains derivable without recording every `AddXP`. |
| Contract | Locations visited and when | 🔵 In progress — awaiting decision | Registry-driven tracking, permanent first-visit persistence, `location.visited` events, and format-3 schema-1 projection are implemented. The canonical non-town location definitions are deliberately deferred; registry version 0 therefore exports an authoritative empty list without claiming coverage. |
| Contract | Towns visited and when | 🟢 Implemented | A TGSRR-owned registry defines stable town IDs and one or more map-reviewed activation points per settlement. Per-point radii range from 200 tiles for compact towns to 350 for Louisville coverage. First entry appends one `town.visited` event and permanently stores its UTC time, world age, triggering point ID, and player coordinates. Format-3 exports every registered town and its first-visit state; migrated runs are marked partial. |
| Contract | Skill books and recipe magazines read and when | 🟢 Implemented | Run initialization records one sorted `literature.baseline` containing only completed PZ literature with a registered `SkillBook` entry or one or more learned recipes. Successful local-player `ISReadABook.complete()` transitions append `literature.read` only for those categories, carrying full item ID, `skill_book`/`recipe_literature` classification, learned recipe IDs, UTC, and world age. Leisure books, ordinary magazines, newspapers, crosswords, and generic print media are excluded. Format-3 exports the filtered baseline and per-item completion summaries; existing broad development state is sanitized and bootstrapped runs remain partial. |
| Contract | Progress for every outpost | 🟢 Implemented | Format-3 exports all 13 stable outpost IDs with discovery/stage state, strict completion, weighted progress, requirement counts, timestamps, and every latest persisted deliverable value. |
| Contract | Completed outposts and completion order | 🟢 Implemented | Format-3 derives an immutable first-completion list from the hash-chained `outpost.completed` events. Each entry includes its chronological completion order, event sequence, UTC, world age, elapsed days since run creation, and requirement totals. Later regression and re-completion do not replace the first completion; bootstrapped runs mark the milestone projection partial. |
| Contract | Kill milestones and elapsed days | 🟢 Implemented | Format-3 exports every hash-chained `kills.milestone.reached` event in sequence order with threshold, observed kill total, character ID, UTC, world age, and elapsed days since run creation. |
| Contract | Skill milestones, including level 10 and elapsed days | 🟡 Planned | Generic level-reached events exist; milestone policy and persistent records remain unfinished. |
| Contract | Outpost milestones and elapsed days | 🟢 Implemented | Format-3 exports the first completion of each outpost deliverable with stable outpost/deliverable IDs, observed value, event sequence, UTC, world age, and elapsed days. Whole-outpost milestones are represented by the ordered completion projection. |
| Contract | Overall challenge progress | 🟢 Implemented | Format-3 exports a rules-versioned map of the Tracker's kills, skills, and outposts summaries. Each retains current, target, normalized progress, availability, and status. No single overall percentage is defined. |
| Contract | Challenge mode | 🟢 Implemented | Every format-3 schema-1 projection contains `challenge.id` and `challenge.gameMode`, preserving Project Zomboid's strings without mapping or inferring eligibility. PZ clears `Core.challengeId` during ordinary save loading, so TGSRR retains the raw ID first observed at challenge startup and uses it when the live field is later empty; a non-empty changed live ID remains visible. Known IDs are `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`; unknown IDs remain valid evidence for website-side mapping and review. |
| Contract | Whether the run remains official | 🔵 In progress — awaiting decision | Run eligibility is website/moderator-owned. The mod will export neutral rule-relevant evidence rather than an authoritative official/unofficial verdict; the complete evidence and policy boundary are still being defined. |
| Contract | Save rollbacks and recovery decisions | 🟡 Planned | The mod-side ledger and neutral recovery-evidence model are designed but not implemented. Eligibility consequences belong to the website/moderator. |
| Contract | Mods used when the run began | 🟢 Implemented | Captures Mod IDs, Workshop IDs, and their mapping. |
| Contract | Mods added or removed during later sessions | 🟢 Implemented | Session-start deltas are recorded, and format-3 also exports the current sorted Mod ID/Workshop ID mapping so consumers need not reconstruct the active state from history. |
| Team request | Distance travelled | 🟢 Implemented | TGSRR follows the established `OnPlayerMove` planar-coordinate pattern used by Twist Stats, treating one world unit as one metre and including vehicle travel. It persists only a monotonic cumulative aggregate, not raw positions. A real-time speed/step bound rejects load jumps and teleports while counting rejected samples. Format-3 exports cumulative metres plus the active day's metre delta; each `day.started` event seals the preceding daily delta. Existing runs are partial. |
| Team request | Animals slaughtered | 🟢 Implemented | TGSRR wraps the successful Build 42 `ISKillAnimal.complete()` and `ISKillAnimalInInventory.complete()` actions for the local player. It records Project Zomboid's raw `IsoAnimal:getAnimalType()` value, a cumulative total, cumulative totals per animal type, and daily deltas per type. Killing an animal through ordinary combat and processing an already-dead carcass are not counted as slaughter. Individual slaughters are deliberately not ledger events, keeping export growth bounded by survived days and observed animal types. Existing runs are partial. |
| Team request | Animals trapped | 🟢 Implemented | TGSRR wraps successful local-player `ISCheckTrapAction.complete()` claims and requires the trap to contain an animal before completion. It preserves PZ's raw trap-animal category (`rabbit`, `squirrel`, `bird`, `mouse`, `rat`, or `raccoon`) and full trap item ID. Format-3 exports the cumulative total plus aggregates by animal category, trap ID, and animal/trap pairing; active and completed days contain pairing deltas from which either dimension can be derived. Individual catches are deliberately not ledger events. Existing runs are partial. |
| Team request | Animal births | 🔴&nbsp;Needs&nbsp;investigation | Establish an authoritative birth event and ownership/world context. |
| Team request | XP gained through skill-book boosts | 🔴&nbsp;Needs&nbsp;investigation | Define attribution when multiple XP modifiers are active and identify the authoritative multiplier state. |
| Team request | Days survived before generator knowledge is learned | 🔴&nbsp;Needs&nbsp;investigation | Identify the stable knowledge/recipe ID and reliable acquisition edge. |
| Team request | Injuries sustained | 🔴&nbsp;Needs&nbsp;investigation | Define injury categories and whether repeated state changes form one injury or several. |
| Team request | Zombie-caused injuries | 🔴&nbsp;Needs&nbsp;investigation | Confirm reliable attacker/source attribution. |
| Team request | Milk collected | 🔴&nbsp;Needs&nbsp;investigation | Trace animal/resource action completion and quantify partial collections. |
| Team request | Butter produced | 🔴&nbsp;Needs&nbsp;investigation | Trace the authoritative crafting/production completion path. |
| Team request | Weapons broken | 🟢 Implemented | TGSRR follows the Build 42 dual path established by Twist Stats: wrap weapon `OnBreak` callbacks and briefly observe condition after `OnWeaponSwing` for weapons without a callback. Weak item-reference deduplication prevents both paths counting the same break. Format-3 exports cumulative ID-sorted totals and active-day deltas, while each `day.started` event seals the preceding daily aggregate. Individual breaks are deliberately not appended to the ledger, keeping long-run growth bounded by survived days and weapon types. Existing runs are partial. |
| Team request | Real time spent in nimble stance | 🔴&nbsp;Needs&nbsp;investigation | Define stance detection, pause handling, and valid active-play accumulation. |
| Team request | Real time spent in the run/stream | 🔴&nbsp;Needs&nbsp;investigation | Define active play versus pause, loading, menus, crashes, and off-stream continuation. |

## Collection principles

- Record stable in-game or TGSRR IDs rather than localized names.
- Prefer authoritative gameplay events over scans where a clean event exists.
- Aggregate high-frequency activity in memory and flush at controlled save/day/session boundaries.
- Append meaningful semantic events and checkpoints, not every sampled value change.
- Preserve world age for canonical run ordering and UTC where stream/session correlation is useful.
- Keep current-state snapshots distinct from historical timelines.
- Do not infer data that Project Zomboid cannot authoritatively expose; retain an explicit unresolved status instead.

## Export implementation reminder

Items marked **Implemented** indicate that their underlying canonical data exists. A separate export implementation pass must still verify that every accepted item is serialized, schema-versioned, integrity-checked, and covered by a representative test run.

## Verified collection boundary

Implementation and persisted test-run audit completed on 2026-07-24:

- World-scoped run state persists immutable run identity, challenge mode, creation
  timestamps, starting character data, selected starting traits, spawned effective
  traits, session sequence, current mod reference baseline, ledger cursor, and the
  active daily baseline.
- The hash-chained event ledger collects session starts and mod deltas, day starts
  and completed-day kill/skill-XP deltas, kill milestones, skill-level events,
  outpost-deliverable completions, and whole-outpost completions.
- Town visitation uses 12 stable town IDs and compact multi-point activation
  rather than unreliable vanilla `TownZone` fragments or hand-authored municipal
  polygons. Hog Wallow Military Base remains a location, not a town.
- Persisted test ledgers contain `session.started`, `day.started`,
  `skill.level.reached`, `outpost.deliverable.completed`, and
  `outpost.completed` records. Rolled-over `day.started` records were verified to
  contain `previousDay`, `killDelta`, and `xpDeltas` payloads.
- The outpost progress store separately persists the latest observation for every
  deliverable and the data required to derive current outpost completion.
- Format-3 currently exports the complete verified event ledger plus a small live
  projection containing the challenge-mode reference, current kills, and
  starting/current character and trait data, plus every current skill's stable
  ID, category ID, level, and cumulative XP, and the full current snapshot of
  all 13 outposts. It also includes the rules-versioned kills, skills, and
  outposts challenge-progress summaries calculated by the Tracker providers and
  the current sorted active Mod ID/Workshop ID mapping. Its active-day snapshot
  adds live kill and per-skill XP deltas without altering sealed history.
- The current projection exports every registered town ID and its permanent
  first-visit state, including the visit timestamps, triggering activation point,
  observed coordinates, and partial-history disclosure.
- Skill-literature history begins with one immutable read-state baseline and
  then uses hash-chained completion deltas. Eligibility comes from PZ's
  registered skill-book metadata or learned-recipe list; generic leisure and
  print-media state is intentionally excluded.
- Deliberate animal slaughter is captured from PZ's two successful `Kill Animal`
  action completions. The current-state snapshot contains the cumulative total
  and raw animal-type totals; day records contain only per-type deltas. No
  per-animal event history is retained.
- Claimed trap catches are captured at successful `Check Trap` completion rather
  than during the unattended hourly catch roll. The current-state snapshot
  contains cumulative animal-category, trap-ID, and paired totals; day records
  contain compact paired deltas. No per-catch history is retained.
- Submission status, run eligibility, and website lifecycle presentation are not
  mod-authored fields. The projection supplies evidence for website-side policy.
