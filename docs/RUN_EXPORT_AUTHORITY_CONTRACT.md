# Run Export Authority Contract

## Purpose

This document maps every format-3 export field to its authoritative website
storage. It is the design contract for replacing projection-only queries with
normalized, searchable records owned by `ChallengeRun`.

The immutable `RunSubmission.raw_export` remains the evidence source. A
submission's decoded projection and ledger are evidence attached to that
submission. They do not become authoritative merely because they were
received. Approval must replace all run-owned authoritative records from the
newly approved export in the same database transaction that marks the
submission approved and updates `ChallengeRun.approved_submission`.

Pending and declined submissions never update run-owned authoritative tables.
Sparse projection sections remain sparse during validation and approval. Missing
catalogue-backed rows represent unexplored, unavailable, or incomplete state and
are resolved against the catalogue only when presentation needs the full expected
set.
Raw identifiers and raw coordinates are retained even when catalogue
resolution succeeds. An unresolved catalogue reference does not reject
otherwise valid evidence unless the field's validation rule explicitly
requires a registered TGSRR identity.

## Common import rules

| Meaning | Rule |
| --- | --- |
| Immutable evidence | Retain `RunSubmission.raw_export`, checksum, decoded envelope metadata, projection, and verified event ledger exactly as received. |
| Current state | Delete and recreate, or deterministically upsert, the complete run-owned current-state set from the newly approved projection. Absence in the latest approved complete projection means absence from current state. |
| Complete history | Rebuild complete run-owned history from the latest approved verified ledger and bounded lifecycle summaries. Never append by trusting only the new tail. |
| Permanent first fact | Preserve the earliest verified occurrence represented by the latest approved complete history. Later exports may repeat it but cannot move it later or rewrite it. |
| Partial evidence | Store each exported `partial` or baseline flag beside the affected aggregate. Do not infer completeness. |
| Catalogue link | Resolve using the exported stable ID and applicable game or registry version. Store both the nullable catalogue foreign key and the raw ID. |
| Atomicity | Decode and validate first. Inside one `transaction.atomic()` block, lock the run and submission, refresh every authoritative row, update the run header, then mark the submission approved. Any failure rolls back all changes. |

## Sparse evidence rules

Projection schema 2 follows an evidence-first sparse contract:

1. Always emit identity, integrity, contract version, ledger head, and the
   current values needed to verify the envelope.
2. Emit an observation when it is non-zero, true, dated, identified, partial,
   or otherwise carries evidence that the website cannot reconstruct.
3. Omit catalogue-backed default rows. The approval importer resolves the
   applicable catalogue version and expands an omitted skill, outpost,
   deliverable, town, or landmark to its known default for presentation.
4. Omit derived duplicates when their value can be reproduced exactly from
   authoritative child rows and the applicable rules version.
5. Omit a `partial` field only when it is false. A true partial flag and any
   accompanying baseline remain mandatory because they qualify the evidence.
6. Do not use omission for an observed negative fact when absence would mean
   unknown. For example, `known = false` after an explicit generator-knowledge
   observation is different from no generator-knowledge observation.
7. Approval always rebuilds current authority from the latest approved complete
   export. Pending and declined sparse exports never fill or clear authority.

This makes absence a contract value, not missing data. Its meaning is defined
per section below and must be tested by both the Lua exporter and Django
importer.

## Envelope and run header

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| envelope format | `ChallengeRun.export_format` | None | Current approved codec format | Replace from approved export. |
| envelope run ID | `ChallengeRun.run_id` | None | Permanent run identity | Must equal the existing run ID; never replace. |
| envelope generated time | `ChallengeRun.generated_at` | None | Current approved snapshot time | Replace. |
| envelope event sequence and hash | `ChallengeRun.event_sequence`, `event_hash` | None | Verified accepted ledger head | Replace after full verification. |
| envelope current kills | `RunKillSummary.current_kills` and compatibility mirror `ChallengeRun.current_kills` | None | Current state | Replace; require equality with `projection.currentKills`. |
| envelope checksum | `RunSubmission.checksum` | None | Immutable submission evidence | Never copy to run authority. |
| `schema` | `RunContractState.projection_schema` | None | Projection contract version | Replace; reject unsupported versions. |
| `lifecycle`, `endedReason`, `endedUtc`, `endedWorldAgeHours`, `endedEventSequence` | `ChallengeRun.lifecycle_status`; `RunLifecycleState.ended_reason`, `ended_utc`, `ended_world_age_hours`, `ended_event_sequence` | None | Current lifecycle plus terminal history anchor | Replace from the approved complete projection and verified terminal event. |
| `challenge.id`, `challenge.gameMode` | `ChallengeRun.challenge_id`, `challenge_game_mode`, `challenge_mode_id` | `ChallengeMode` | Current challenge evidence | Replace raw values and resolver link. |

## Character, starting location, traits, and occupation

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `character.starting.forename`, `surname`, `displayName` | `RunCharacter.starting_forename`, `starting_surname`, `starting_display_name` | None | Permanent starting identity metadata | Replace only from the complete approved projection; history comparison must prevent rewriting. |
| `character.starting.professionId` | `RunCharacter.starting_occupation_raw_id`, `starting_occupation_id` | Occupation | Permanent starting build | Resolve and retain raw ID. |
| `character.current.*` | `RunCharacter.current_forename`, `current_surname`, `current_display_name`, `current_occupation_raw_id`, `current_occupation_id` | Occupation | Current state | Replace. Mirror current display name to `ChallengeRun.character_name`. |
| `character.chosenStartingRegion.schema`, `selectionMode`, `resolvedRegionId`, `capturedUtc` | `RunStartingLocation.chosen_region_schema`, `selection_mode`, `resolved_region_raw_id`, `chosen_region_captured_utc` | Town or versioned starting-area entry | Permanent pre-spawn evidence | Preserve whether the player explicitly chose a region or committed to Random, plus the region resolved at final Start. Retain the raw map-region ID. |
| `character.selectedStartingTraits[]` | `RunCharacterTrait` with phase `selected_starting` | Trait | Permanent starting build | Rebuild ordered/set rows; retain raw IDs. |
| `selectedStartingTraitsPartial`, `selectedStartingTraitsCapturedUtc` | `RunCharacter.selected_traits_partial`, `selected_traits_captured_utc` | None | Evidence quality and capture time | Replace. |
| `startingEffectiveTraits[]` | `RunCharacterTrait` with phase `spawned_starting` | Trait | Permanent spawned state | Rebuild rows. |
| `currentEffectiveTraits[]` | `RunCharacterTrait` with phase `current` | Trait | Current state | Replace rows. |
| `startingLocation.x`, `y`, `z` | `RunStartingLocation.x`, `y`, `z` | Optional map version | Permanent evidence | Create or replace from the complete projection, while approval history checks prohibit mutation. |
| `startingLocation.buildingId` | `RunStartingLocation.building_def_id` | None | Permanent raw PZ evidence | Store as text for precision safety. |
| `startingLocation.capturedUtc`, `worldAgeHours`, `partial` | `RunStartingLocation.captured_utc`, `world_age_hours`, `partial` | None | Permanent capture provenance | Store exactly. |
| `startingLocation.registeredLocation.kind`, `id`, `registryVersion` | `RunStartingLocation.registered_kind`, `registered_raw_id`, `registry_version`, `catalogue_entry_id`, `map_location_version_id` | Outpost or Location | Stable resolved identity at capture | Resolve by kind, ID, and registry version; fields may be absent for ordinary spawns. |

### Player-facing starting-location presentation

The signed-in run page presents only two concise rows:

- **Spawn choice:** show `Random Spawn, KY` when `selection_mode` is
  `random`. For an explicit selection, show the resolved region's catalogue
  display name, falling back to its preserved raw region ID.
- **Starting location:** show the plain `x, y` coordinates followed by a
  separate `View map` external link to
  `https://map.projectzomboid.com?{x}x{y}x{z}`. The URL always retains the
  observed Z coordinate even when the visible label omits level zero. The link
  opens in a new tab, carries an external-link indicator, and uses the
  accessible label `View starting location on the Project Zomboid Map`.

The resolved region chosen for a random selection remains retained evidence
but is not revealed in the ordinary player-facing summary.

BuildingDef ID, capture times, schema, registry version, partial status, and
other provenance remain retained evidence but are not shown in this ordinary
player-facing panel.

## Recovery, sessions, lifecycle, and mod history

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `recovery.schema`, `present`, `hasBranches`, `status`, `activeEpoch` | `RunRecoveryState.*` | None | Current recovery state | Replace. |
| `recovery.recoveries[]` | `RunRecoveryRecord` | None | Complete verified recovery history | Rebuild from export, including superseded event bodies and cursors. |
| `recovery.decisions[]` | `RunRecoveryDecision` | None | Complete verified decision history | Rebuild with decider type and ID retained. |
| ledger envelope fields on every event | `RunEvent.schema`, `epoch`, `sequence`, `utc`, `world_age_hours`, `event_type`, `payload`, `event_hash` | Conditional | Complete verified history | Rebuild all rows from the verified ledger, unique by run and sequence. |
| `session.started` character, challenge, mod state, mods and deltas | `RunSession` and `RunSessionModChange` | Mod and ChallengeMode | Complete session and mod history | Derive from every session event; preserve raw Mod ID and Workshop ID pairing. |
| `run.debug.enabled` | `RunDebugObservation` | None | Complete neutral review evidence | Derive from ledger; never auto-decline. |
| `run.clock.repaired` | `RunClockRepair` | None | Complete clock-reconciliation evidence | Derive from ledger, retaining saved and observed clock evidence plus the recorded decision. |
| `run.ended` | `RunLifecycleEvent` | None | Permanent terminal milestone | Derive from ledger and cross-check projection terminal fields. |
| `activeMods[].modId`, `workshopId` | `RunCurrentMod.raw_mod_id`, `raw_workshop_id`, `catalogue_entry_id` | Mod | Current state | Replace complete set. Workshop ID is not a substitute for Mod ID. |

## Skills, XP, daily statistics, weight, distance, and activity

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `skills[].id`, `categoryId`, `level`, `xp` | `RunSkill.raw_skill_id`, `raw_category_id`, `level`, `xp`, `catalogue_entry_id` | Skill | Sparse current state | Replace non-zero skill rows. An omitted catalogue skill means level 0 and XP 0. |
| `skill.level.reached` | `RunSkillLevelEvent` | Skill | Complete level history | Derive from ledger. |
| `skill.milestone.reached` | `RunSkillMilestone` | Skill | Complete configured skill-milestone history | Derive from ledger and cross-check the milestone projection. |
| `milestones.skillMilestones[]` | `RunSkillMilestone` | Skill | Permanent first level-10 facts | Rebuild fixed set and cross-check ledger. |
| `milestones.killMilestones[]` | `RunKillMilestone` | None | Permanent first kill-threshold facts | Rebuild fixed set and cross-check ledger. |
| `activeDay.dayIndex`, start and observation UTC/world age, `elapsedWorldHours`, `baselinePartial` | `RunActiveDay` | None | Current unsealed day | Replace one row. |
| `activeDay.killDelta`, `xpDeltas{skillId: value}` | `RunActiveDay.kill_delta`; `RunActiveDaySkillXp` | Skill | Current unsealed day | Replace scalar and non-zero skill rows. |
| `day.started` day metadata and `completedDay` | `RunDailyRecord` state `sealed`, plus sparse `RunDailyMetric` rows | Conditional | Complete sealed daily history | Rebuild all days from ledger; missing compact delta means zero. |
| `weight.currentKilograms`, `weight.unit` | `RunWeightState.current_kilograms`, `unit` | None | Current state | Replace. |
| daily and active `weightDeltaKilograms` | `RunDailyRecord.weight_delta_kilograms` | None | Complete sealed history and current day | Rebuild/replace by record state. |
| `distance.travelledMeters`, `rejectedSamples`, `partial`, `unit` | `RunDistanceSummary.*` | None | Current cumulative state | Replace. |
| daily and active `distanceDeltaMeters`, partial flag | `RunDailyRecord.distance_delta_meters`, `partial_metrics` | None | Complete sealed history and current day | Rebuild/replace by record state. |
| `nimbleStance.movementMilliseconds`, `partial`, `unit` | `RunActivitySummary.nimble_movement_milliseconds`, `nimble_partial` | None | Current cumulative state | Replace. |
| `activeGameplay.milliseconds`, `partial`, `unit` | `RunActivitySummary.active_gameplay_milliseconds`, `active_gameplay_partial` | None | Current cumulative state | Replace. |

## Challenge progress, outposts, and deliverable lifecycle

`challengeProgress` is presentation-only derived state and is not part of the
sparse export contract. The website calculates category values, targets,
ratios, percentages, availability, and status from approved typed kill, skill,
outpost, and landmark authority plus the applicable versioned catalogues.
Legacy exports containing `challengeProgress` remain valid evidence, but the
field is ignored during authority refresh and public presentation.

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `outposts[].id` | `RunOutpost.raw_outpost_id`, `catalogue_entry_id` | Outpost | Current state identity | Replace all registry members. |
| `discovered`, `discoveredWorldAgeHours`, `workStartedWorldAgeHours` | `RunOutpost.*` | Outpost | Permanent first facts exposed in current snapshot | Replace from complete history, cross-check earliest events when available. |
| `stage`, `complete`, `progress`, `passedRequirements`, `totalRequirements` | `RunOutpost.*` | Outpost | Current derived state | Replace. |
| `outposts[].deliverables[]` raw ID, stage, completion, progress, values, requirements and observation fields | `RunOutpostDeliverable.*` | Deliverable | Current state | Replace the complete fixed deliverable set per outpost. Retain raw observed values as JSON only where the deliverable has genuinely heterogeneous evidence. |
| deliverable lifecycle `firstCompletion` | `RunOutpostDeliverable.first_completed_*` | Deliverable | Permanent first milestone | Rebuild from complete lifecycle summary and ledger. This is the only permanent deliverable milestone. |
| deliverable lifecycle `latestCompletion`, `latestRegression`, `completionCount`, `regressionCount`, `currentState` | `RunOutpostDeliverable.latest_completed_*`, `latest_regressed_*`, `completion_count`, `regression_count`, `current_state` | Deliverable | Bounded complete lifecycle summary | Replace from the latest approved export. Later transitions update counts and latest observations without growing the ledger. |
| whole-outpost lifecycle fields with the same six-part model | `RunOutpost.first_completed_*`, `latest_completed_*`, `latest_regressed_*`, `completion_count`, `regression_count`, `current_state` | Outpost | Bounded complete lifecycle summary | Apply the same rule as deliverables. |
| first `outpost.deliverable.completed` event | First-completion evidence on `RunOutpostDeliverable` | Outpost and Deliverable | Sole permanent deliverable milestone | Require exactly one matching ledger event when the completion count is positive. Later completions and regressions are not ledger events. |
| first `outpost.completed` event | First-completion evidence on `RunOutpost` | Outpost | Sole permanent whole-outpost milestone | Require exactly one matching ledger event when the completion count is positive. Later completions and regressions are not ledger events. |
| `milestones.outpostDeliverableMilestones[]` | Compatibility input to first-completion fields | Outpost and Deliverable | Permanent first completion only | Validate against lifecycle summary and ledger, then stop presenting it as the whole lifecycle. |
| `milestones.outpostCompletions[]` | Compatibility input to first-completion fields | Outpost | Permanent first completion only | Validate against lifecycle summary and ledger. |

The first-completion point carries its ledger event sequence, UTC, world age,
and elapsed challenge days. Later latest-completion and latest-regression
observations carry UTC, world age, and elapsed days but no event sequence.
Counts are non-negative and `currentState` matches the latest observed state.
The run save owns these bounded counters and latest observations.

Projection schema 2 is sparse. Omitted outposts, deliverables, towns, and
landmarks mean the versioned catalogue default: undiscovered, unvisited,
incomplete, zero lifecycle counts, and no timestamps. Approval expands that
sparse evidence into the complete 13-outpost and 169-deliverable run authority.
All fields named `partial`, ending in `Partial`, or named `baselinePartial`
default to `false` when omitted and are emitted only when true.

## Towns, landmarks, and literature

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `townVisits.partial` | `RunTownHistory.partial` | None | History quality | Replace. |
| `townVisits.towns[].id`, first visit UTC/world age, point ID, XYZ | `RunTownVisit.*` | Town and map version | Sparse permanent first visits | Expand omitted catalogue members as unvisited, retaining raw point and coordinates for present rows. |
| `town.visited` | `RunTownVisitEvent` | Town | Complete first-visit ledger history | Rebuild and cross-check projection. |
| `locations.schema`, `registryVersion`, `partial` | `RunLocationHistory.*` | None | Registry and history quality | Replace. |
| `locations.entries[].id` and visit evidence | `RunLocationVisit.*` | Location and map version | Sparse permanent first visits | Resolve by exported ID/version. Omitted catalogue members are unvisited; names, categories, bounds, anchors, and expected BuildingDefs come from the website catalogue. |
| `location.visited` | `RunLocationVisitEvent` | Location | Complete first-visit ledger history | Rebuild and cross-check projection. |
| `literature.schema`, `partial` | `RunLiteratureHistory.*` | None | Contract and history quality | Replace. |
| baseline capture UTC/world age and baseline item sets | `RunLiteratureBaseline` and `RunLiteratureBaselineItem` | Item | Permanent baseline | Rebuild from export; retain legacy title/print-media sets if still exported. |
| current item/title/print-media sets | `RunCurrentLiteratureItem` | Item | Current state | Replace complete sets. |
| `literature.completed[]` | `RunLiteratureCompletion` | Item and Recipe | Complete first/latest/count summary per item | Rebuild from projection and cross-check read events. |
| `literature.baseline`, `literature.read` ledger events | `RunLiteratureEvent` | Item and Recipe | Complete verified history | Rebuild. |

## Kills and weapon attribution

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `currentKills` | `RunKillSummary.current_kills` | None | Current authoritative PZ kill count | Replace. |
| `weaponKills.partial`, `baselineTotal` | `RunKillSummary.weapon_partial`, `weapon_baseline_total` | None | Attribution quality | Replace. The whole section is omitted when complete, zero, and source-free. |
| `weaponKills.sources[].id`, `kills` | `RunWeaponKill.raw_source_id`, `kills`, `catalogue_entry_id` | Item when source is an item | Sparse current cumulative state | Replace positive sources; preserve TGSRR pseudo IDs unresolved. Omitted sources mean zero. |
| daily and active weapon-kill maps | `RunDayWeaponKill`, `RunActiveDayWeaponKill` | Item | Complete daily history and current day | Rebuild/replace non-zero rows. |
| `fireDeaths.count`, `partial` and daily/active deltas | `RunKillSummary.fire_deaths`, `fire_deaths_partial`; fields on `RunDay` and `RunActiveDay` | None | Separate cumulative and daily evidence | Replace/rebuild; never add to player or weapon kills. Omitted section means complete zero. |
| `zombieKillTypes.standing`, `onfront`, `onback`, `fenceAssist`, `windowAssist`, `partial` | `RunKillSummary.standing`, `on_front`, `on_back`, `fence_assist`, `window_assist`, `zombie_kill_types_partial` | None | Sparse current cumulative classification | Replace present values and default omitted members to zero. Omitted section means complete zero. |
| kill milestone projection and ledger events | `RunKillMilestone` | None | Permanent first threshold facts | Rebuild and cross-check ledger. |

## Injuries

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `injuries.partial` | `RunInjurySummary.partial` | None | History quality | Replace. |
| `injuries.all.total`, `byType[]`, `byBodyPart[]`, `pairs[]` | `RunInjurySummary.total`; `RunInjuryAggregate` with scope `all` | None | Current cumulative state | Replace all aggregates, preserving raw injury and body-part IDs. |
| corresponding `zombieAssociated` fields | Same tables with scope `zombie_associated` | None | Current cumulative neutral evidence | Replace; do not present as guaranteed wound source. |
| daily and active injury delta arrays | `RunDayInjury`, `RunActiveDayInjury` | None | Complete daily history and current day | Rebuild/replace by scope, raw type, and raw body part. |

## Animals, fishing, milk, butter, consumption, and calories

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `animalsSlaughtered.total`, `partial`, `animalTypes[]` | `RunAnimalSummary` kind `slaughter`; `RunAnimalAggregate` | Animal | Current cumulative state | Replace, retaining raw animal type. |
| `animalsTrapped.total`, `partial`, `animalTypes[]`, `traps[]`, `pairs[]` | Summary and `RunTrapAggregate` | Animal and trap Item | Current cumulative state | Replace all three views; paired rows are canonical for daily deltas. |
| `animalBirths.total`, `partial`, `animalTypes[]` | Animal summary/aggregate kind `birth` | Animal | Current cumulative state | Replace. |
| `animalsPetted.total`, `partial`, `animalTypes[]` | Animal summary/aggregate kind `pet` | Animal | Current cumulative state | Replace. |
| daily and active slaughter, trap, and birth deltas | Typed `RunDayAnimal*` and `RunActiveDayAnimal*` rows | Animal and Item | Complete daily history and current day | Rebuild/replace. |
| `fishCaught.total`, `partial`, `fish[]` | `RunFishSummary`; `RunFishCatchAggregate` | Item | Current cumulative state | Replace. |
| daily and active fish deltas | `RunDayFishCatch`, `RunActiveDayFishCatch` | Item | Complete daily history and current day | Rebuild/replace. |
| `milkCollected.unit`, `total`, `partial`, `milkTypes[]` | `RunMilkSummary`; `RunMilkAggregate` | Item or raw fluid catalogue when added | Current cumulative state | Replace, preserving raw milk type. |
| daily and active milk deltas | `RunDayMilk`, `RunActiveDayMilk` | Same | Complete daily history and current day | Rebuild/replace. |
| `butterProduced.itemId`, `count`, `partial` | `RunProductionSummary` kind `butter` | Item | Current cumulative state | Replace and require the declared item ID for this schema. |
| daily and active butter delta | `RunDay.butter_produced`, `RunActiveDay.butter_produced` | Item | Complete daily history and current day | Rebuild/replace. |
| `fluidConsumed.unit`, `totalLiters`, `partial`, `fluidTypes[].fluidTypeId`, `liters` | `RunConsumptionSummary`; `RunFluidConsumption` | Raw fluid ID, future fluid catalogue | Current cumulative state | Replace. Mixtures remain explicit raw types. |
| `caloriesConsumed.unit`, `totalKilocalories`, `partial` | `RunConsumptionSummary.calories_*` | None | Current cumulative state | Replace. Do not derive from current Nutrition balance. |

## Broken weapons, generator knowledge, and repairs

| Export field | Authoritative table and column | Catalogue link | Meaning | Approval import rule |
| --- | --- | --- | --- | --- |
| `brokenWeapons.total`, `partial`, `weapons[]` | `RunBrokenWeaponSummary`; `RunBrokenWeapon` | Item | Current cumulative state | Replace all weapon rows. |
| daily and active broken-weapon deltas | `RunDayBrokenWeapon`, `RunActiveDayBrokenWeapon` | Item | Complete daily history and current day | Rebuild/replace. |
| `generatorKnowledge.schema`, `recipeId`, `known`, first-observed UTC/world age, survived days, baseline/partial flags | `RunGeneratorKnowledge.*` | Recipe | Current state plus permanent first observation | Replace and cross-check ledger first-observed event. |
| generator evidence profession, Electrical level, Inventive, magazine completed | `RunGeneratorKnowledge.*_evidence` | Occupation, Skill, Trait, Item | Neutral contemporaneous evidence | Replace raw values and resolved links; never infer the source. |
| `knowledge.generator.first_observed` | `RunGeneratorKnowledgeEvent` | Recipe | Permanent first observation | Rebuild from ledger. |
| `generatorRepairs.count`, `conditionRestored`, `partial` | `RunGeneratorRepairSummary.*` | None | Current cumulative state | Replace. |

## Projection-only and ledger-only boundaries

- Projection aggregates are accepted current state only after approval.
- Ledger rows are accepted complete verified history only after approval.
- Bounded lifecycle summaries bridge current state and repeated transition
  history without allowing the ledger or export to grow per transition.
- Raw projection JSON and raw event JSON remain on the submission for evidence
  inspection, but public graphs, rankings, filters, records, and statistics must
  query only run-owned authoritative tables.
- `ChallengeRun.latest_projection` and `latest_events` are compatibility caches,
  not the long-term query authority. They may remain during migration but must
  only be refreshed inside the same approval transaction.

## Implementation order

The initial authority slice is implemented: contract state, character,
three trait phases, starting location, catalogue links, atomic approval refresh,
and the player-facing spawn summary.

The outpost lifecycle slice is also implemented. Projection schema 2 exports
only outposts and deliverables carrying non-default state or evidence. The
website expands the sparse projection to all 13 outposts and 169 deliverables,
verifies each first completion against its sole permanent ledger event, and
atomically rebuilds run-owned authority. Later completion and regression
transitions update bounded counts and latest observations only.

Skills and the first kill-authority slice are implemented. The exporter omits
zero-level, zero-XP skills and empty complete kill-attribution sections. Approval
rebuilds `RunSkill`, `RunKillSummary`, and `RunWeaponKill` rows, retaining partial
baselines and raw identifiers.

The daily authority framework is implemented. Sealed `completedDay` snapshots
are rebuilt from the immutable `day.started` ledger, and the projection's
`activeDay` becomes one replaceable active record. Scalar deltas use fixed
columns. Keyed non-zero deltas use sparse `RunDailyMetric` rows with raw IDs and
catalogue links where a suitable catalogue exists. Missing values mean zero,
and partial provenance remains explicit. Poll decisions can therefore enable
or disable individual emitted metric kinds without another table redesign.

The remaining sequence is:

1. Add normalized run header extensions, landmarks, and their remaining
   catalogue links.
2. Add the remaining typed aggregate and history tables in the sections above.
3. Expand the approval service until it locks, validates, refreshes, and
   approves every authoritative section atomically.
4. Move graphs, filters, public records, and remaining run presentation from
   projection JSON to authoritative tables.
5. Retain compatibility JSON until parity tests prove every exported field is
   imported and presented from normalized authority.
