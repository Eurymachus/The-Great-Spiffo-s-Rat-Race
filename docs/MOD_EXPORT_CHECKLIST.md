# Mod: Export Data Checklist

## Farming statistics (21 November 2026)

- Implemented in 42.22: verified ploughed-to-seeded sowings and successful
  harvests by raw crop key, plus actual harvested produce by full item type.
  Credit follows the local harvester, regardless of vanilla plant owner.
- Successful completion and authoritative plant-state changes are required;
  cancelled/foreign/stopped-run actions and duplicate callbacks do not count.
  Regrowth harvests count again. Seed consumption alone does not prove sowing.
- Harvest-only before/after output counts are capped by the observed vanilla
  yield roll. This excludes extra seeds even where seedName and vegetableName
  are the same item (corn, peppers, barley). Extra produce is included; seed-only
  items and ordinary looting are excluded. No yield reroll or per-tick scanning.
- `farming` exports independent cumulative `planted`, `harvested` and `produce`
  maps, schema 1 and partial coverage. Daily maps are `farmingPlantedDeltas`,
  `farmingHarvestedDeltas`, `farmingProduceDeltas`. Approval stores separate
  summaries and crop/item dimensions. Existing saves have partial coverage.
- Installed vanilla-action/harvest Lua tests, daily rollover/reload regressions,
  23 focused website tests, syntax and prohibited-global checks pass.
- In-game test confirmed on 22 November, run
  `rr-1795374245-1795374245421-744936-711157`: three plantings,
  Basil 1, BellPepper 1 and BlackSage 1. Subsequent export records one Basil
  harvest and four `Base.Basil` produce items; planting counts remain unchanged.
  Both exports pass website validation; cumulative and day-1 deltas agree.
  Harvest was tested after debug-assisted crop growth. This confirms capture,
  not natural growth timing.
- Repeat-harvest and daily-rollover test confirmed on 22 November in the same
  run: cumulative plantings remain Basil 1, BellPepper 1 and BlackSage 1.
  Harvests are Basil 2, BellPepper 1 and BlackSage 1; produce totals are
  `Base.Basil` 8, `Base.BellPepper` 2 and `Base.BlackSage` 3.
  Sealed day 1 contains both Basil harvests and the BlackSage harvest (11
  produce items); active day 2 contains the BellPepper harvest (2 items),
  with no new plantings. The export passes validation and daily sums exactly
  match the independent cumulative totals: 3 plantings, 4 harvests, 13 items.
  This confirms repeat Basil harvesting from one planting and daily rollover.
  Seed-bearing yield separation, cancellation and save/reload remain separate
  outstanding in-game checks.
- Terminal-export test confirmed on 22 November in the same run:
  projection lifecycle and `run.ended` event sequence 7 both report `deceased`.
  Export validation passes. Farming totals remain 3 plantings, 4 harvests and
  13 produce items; sealed day 1 and active day 2 counts remain unchanged and
  agree with cumulative totals. This verifies farming evidence survives the
  death/terminal export, not save/reload or attempted post-death collection.
- Team Test refreshed on 22 November; all 616 mod files verified against source.
  The C: and E: profile paths are aliases for the same physical package,
  not two independent copies. Workshop metadata preserved; no upload.
  The earlier export lacked farming coverage because the package was stale.


## Cooked food collected (21 November 2026)

- Implemented in 42.22: successful solo transfers and ground pickups into the
  player's inventory/carried bags, including food inside acquired bags. Eligible
  Food items are cooked or tagged AlreadyCooked, and not burnt. No chef attribution.
- Persistent item ModData `TGSRRCookedFoodRunId` prevents the same item counting
  again after storage, retrieval, repeated callbacks or reload. Existing carried
  food is baselined once without credit when the collector is introduced.
- Cumulative raw full-item-type counts are independent of daily history.
  `cookedFood = {schema = 1, items = {...}, partial = true?}` exports with sparse
  `cookedFoodItemsDeltas` and coverage metadata. Approval normalizes item metrics
  and a cumulative summary. Missing historical coverage remains unknown.
- Keep this slice simple: no recipe/portioning marker propagation, cooking-XP
  inference, appliance scanning or per-item export ledger. New items created by
  slicing or transformations may count separately on later collection.
- Desktop collector, daily rollover/reinitialization and website validation tests
  pass. In-game transfer, whole-bag pickup, save/reload and midnight acceptance
  remain pending. Both local Team Test copies updated and all 614 mod files
  verified on 21 November. Workshop metadata preserved; no upload.


## Purpose

This is the working checklist for the player/run data that TGSRR intends to collect and ultimately include in a Rat Race export. Update the status and implementation notes as collectors, persistence, integrity handling, and export serialization are completed.

TGSRR is always the sole authority for this data. Installed unrelated mods do not supply, replace, or alter any item in this checklist. The Tracker is TGSRR's player-facing presentation of the canonical state.

## Statistics readiness audit (20 November 2026)

Scope: static trace of the current 42.22 collectors, Runtime initialization,
Exporter projection, website approval and normalized authority, plus existing
regression tests. This is not a fresh in-game validation of every collector.
Compared with the live [Brazilian statistics page](https://www.pzrank.com.br/estatisticas).
No new collection or public statistics page is implemented by this audit.

### Data already collected and exported

| Family | Available evidence | Website work / interpretation |
|---|---|---|
| Participants and runs | Website participant identity, TGSRR run identity, starting timestamps, challenge mode, terminal lifecycle/timestamps | Count distinct runs and accounts, not submissions. Define eligibility, mode and build filters. Registered accounts and participating accounts are different populations. |
| Character builds | Starting/current occupation and sex; selected starting, spawned effective and current trait sets | Normalized RunCharacter and RunCharacterTrait support popularity, repeated builds and descriptive comparisons. Choose the correct trait phase; current traits are not original choices. |
| Spawn geography | Chosen region and observed starting XYZ/building, partial provenance | RunStartingLocation exists. Map raw region/tile evidence to a versioned geography; distinguish chosen region from actual spawn. |
| Survival | Day starts, active day, terminal time, active gameplay milliseconds | Survival distributions and weekly starts/deaths are derivable. Active runs are ongoing observations, not completed lifetimes. Submission recency does not prove recent play. |
| Combat | Vanilla kills, daily kills, per-item/pseudo-source weapon kills, separate fire deaths; cumulative posture/fence/window categories | RunKillSummary, RunWeaponKill and daily records exist. Fire deaths are not player-credited kills. Weapon category grouping needs catalogue mapping. Posture/assist counts have no daily breakdown. |
| Skills | Current levels/XP, daily XP deltas, skill-level events and first level-10 milestones | RunSkill and daily metrics exist. Level-10 timing is already exported; generic milestone analytics need normalization. Level zero is sparse and must be reconstructed from the applicable registry. |
| Outposts | Current requirements/progress, first/latest completion, latest regression, counts and first-completion order | RunOutpost and RunOutpostDeliverable exist. Supports completion rates, order and milestone timing. No complete chronological log of every later regression or every unfinished requirement value. |
| Towns and landmarks | First visits with stable IDs, timestamps and observed coordinates | RunLandmark is normalized. Town visits remain in approved projection/events; add normalized town authority for community analytics. Visits do not prove clearing or looting. |
| Literature | Skill-book/recipe-literature baseline, first read evidence, item IDs and learned recipes | Exported but no dedicated literature authority table. Excludes leisure books and ordinary magazines. Baseline reads do not have invented original read times. |
| Movement and time | Total planar distance plus on-foot/driving metres, rejected movement samples, active gameplay time and on-foot moving-aim time | Normalized cumulative/daily statistics exist. Tick-based travel categories, save/reload and daily rollover are verified in game; known-route accuracy remains unverified. Previous movement-event totals did not reliably include vehicles. Active gameplay is not stream duration. |
| Health and weather | Daily/current body weight, observed outdoor temperature extrema, injury type/body-part pairs and zombie-associated subset | Normalized summaries/daily records exist. Injury transitions are not every damage hit; zombie association is evidence, not guaranteed causation. Weather values are sampled outdoor extrema, not body temperature or daily means. |
| Wildlife and husbandry | Slaughter actions, claimed trap catches by animal/trap pairing, domestic births, petting, fish landed by item type, milk litres by fluid | Normalized totals/daily dimensions exist. Slaughter excludes ordinary animal combat kills; fishing excludes nets and trash. No current herd inventory or general species-encounter tracker. |
| Consumption and production | Calories consumed, manual fluid consumption by type, butter produced | Normalized cumulative/daily values exist. Butter is a specific recipe tracker, not general crafting. Consumed water is not collected water; consumed calories are not meals cooked. |
| Equipment and generators | Weapons broken by item, generator repair count/condition restored, first generator-knowledge observation with context | Repairs/breaks normalized. Knowledge milestone is exported but needs analytics normalization. Knowledge observation does not conclusively identify its source. |
| Sessions and mods | Session starts, initial and changed mod/Workshop IDs, debug observations, recovery branches | Available as evidence. Population mod-use charts need approved, normalized mappings and a defined initial/current/history scope. Exclude superseded recovery branches from totals. |

### Genuine additional tracking candidates

All remain proposals; API feasibility and runtime cost need verification before
implementation. A new metric needs collection, persistence, export validation,
approval normalization, coverage metadata and presentation together.

| Candidate seen on Brazilian page | TGSRR gap and proposed counting boundary |
|---|---|
| Death causes and death regions | TerminalState records death and time, not cause or final location. Add terminal observations with explicit unknown/uncertain classification; injuries cannot substitute for cause. Capture a coarse region or map a terminal tile, rather than inferring it from the last town visited. |
| Items/materials/weapons/forged weapons/clothes/furniture/ceramics made | Add successful recipe/output collection, stable recipe and item IDs, quantities and versioned category mapping. Distinguish recipe executions from output units, cancellation from completion, and intermediate materials from finished tools. Coordinate with the separately approved outpost crafting-provenance work; aggregate counts do not prove provenance of a stored item. |
| Structures and stone structures built; workstations used | Add successful construction actions and actual successful station use. Separate unique stations from action counts and repairs/dismantling. |
| Crops planted and harvested; meals cooked | New successful-action collectors. Define harvest actions versus item yield and cooking transitions versus recipe executions. |
| Eggs collected and cheese produced | New collection/production hooks. Existing milk and butter tracking does not cover these. |
| Trees cut and animal tracks followed | New completed-action tracking with a clear tree/track identity or action-count definition. |
| Houses looted, doors opened, basements explored | Existing internal buildingVisits proves first entry only and is not exported. Export compact visit summaries for exploration, or separately define actual looting. Doors need distinct-door versus repeated-action semantics; basements need stable identity. |
| Kilometres driven | Implemented on-foot and driving counters with daily deltas. Mode separation, reload and rollover verified in game; measured-route accuracy remains pending. Historical totals cannot recover the split. |
| Distinct sleeping places and longest awake interval | New sleep start/end observations, stable place grouping and game-time duration. No existing sleep history. |
| Days without canned food | Existing calorie totals do not retain food identity. Track qualifying consumption and streak start/end with explicit food-category rules. |
| Water collected | Track acquisition separately from drinking; prevent transferring the same water between vessels repeatedly counting as new collection. |
| Animal species | Existing action-specific type sets can answer species fished/trapped/slaughtered/petted. General species encountered or owned requires separate observation and a definition. |

Brazilian presentation ideas requiring no new game tracking include medians,
histograms, weekly run starts/deaths, popular/repeated trait builds, weapon
preference versus survival, skill-level distributions, records and descriptive
comparisons. Add minimum sample sizes and coverage counts. Their named seasons
and inactivity thresholds are policies, not existing TGSRR definitions.

### Reconciliation with parked ideas

- Aggregate trait/weapon charts and richer approved-run chronology remain
  website presentation work. The underlying evidence largely exists.
- The parked generic per-day aggregate proposal is partly stale: many daily
  families are already exported and normalized. Extend only specific gaps.
- Coarse kill/death heatmaps, sleeping areas, basement exploration and canned-
  food streaks remain unimplemented proposals. Town/landmark first visits are
  already implemented but are not a continuous exploration trail.
- The old reference to collectible evidence in approved exports is not backed
  by a general collectible collector in the current code. Special relics at
  selected locations are separately parked, new-run-only work.
- XP attributed specifically to skill-book boosts and hunger fulfilled remain
  explicitly deferred. Correlating reading with XP is possible; claiming the
  book caused a precise amount of XP is not supported.
- Milestone timings and daily summaries suggested in the conversation are
  already implemented in substantial part, not new collector requirements.

### Evidence and validation

- Mod: `42.22/media/lua/client/TGSRR/Run/Runtime.lua`, `Exporter.lua`,
  `DayTracker.lua`, `EventBridge.lua`, `MilestoneSnapshot.lua`,
  `TerminalState.lua`, and the named per-family trackers/snapshots.
- Website: `registry/submission_approval.py`, `run_authority.py`, `models.py`,
  `run_public.py`, and `test_run_exports.py`.
- Approval refreshes normalized authority from approved evidence. Community
  analytics should follow the 18 August decision in DECISIONS.md: query
  normalized authority, not repeatedly decode projection JSON. Towns,
  literature, generic milestones and generator knowledge need additional
  normalization for that use, even though their export evidence exists.
- Five existing focused tests passed: cumulative statistic normalization,
  sealed/active daily authority, sparse skills/kills, outpost reconstruction,
  and isolation of pending/declined updates from approved runs.
- Preserve per-family partial/missing semantics. Missing old observations are
  not automatically zero; absent sparse deltas within a supported contract
  can mean zero. Cumulative totals are independently authoritative and must
  not be replaced by sums of daily records.
- No game-side changes, live data mutations, deployment or fresh in-game
  collector validation were performed. Recommended next decision: choose the
  first statistics-page questions from existing evidence, then approve a small
  explicit shortlist of additional collectors.

## Terminal death evidence first slice (21 November 2026)

- Implemented for 42.22; tested in-game examples are in `MOD_NOW.md`. `DeathEvidence`
  listens to `OnPlayerGetDamage` only for the active tracked player and retains
  the latest positive finite amount per source, up to 32 sources, within ten
  real-time seconds. Amounts are individual callback values, not cumulative
  damage or a guaranteed decomposition of terminal health loss. No hit events
  or continuous positions are appended to the ledger.
- `OnPlayerDeath` captures tile XYZ, optional building ID and registered
  outpost/landmark, plus `isKilledByFall()` and `isDeathDragDown()`. The existing
  terminal event and export projection carry the identical versioned snapshot.
  Fall/drag-down flags select an explicit classification; conflicting flags
  remain mixed. Otherwise the most recent source is suspected, or unknown if
  absent/stale. Other recent sources retain their ages and callback order.
- Capture context distinguishes the death callback from post-death UI recovery.
  Recovery does not reconstruct recent damage. Missing coordinates and flags
  remain unknown; repeated exports do not overwrite the successful capture.
  The ten-second window is not complete across reloads, initialization or
  recovery; no old damage history is invented. Pauses count toward real time.
- Website validation accepts older exports with no death evidence, rejects
  malformed/mismatched observations, and normalizes only approved evidence into
  `RunDeathSummary` and `RunDeathDamage`. Pending submissions cannot change those
  rows. Region mapping and public death statistics remain future presentation work.
- Source verification: installed build `26486631`, decompile job 17.
  `IsoPlayer.OnDeath` emits the local-player callback before vehicle exit.
  `IsoGameCharacter` publicly exposes both terminal flags through its exposed
  class. `BodyDamage.Update` can emit multiple damage types after a combined
  reduction, so event order is not proof of cause. `BaseVehicle.damagePlayers`
  provides `CARCRASHDAMAGE` on its non-client path; multiplayer coverage is not
  established. `CARHITDAMAGE` is separate. No speed-drop heuristic is used.

In-game validation, using disposable local test runs:

1. Start with a fatal fall: check `console.txt` for `[TGSRR Run] Death evidence`,
   `cause=fall`, `certainty=explicit_flag`, and the correct landing XYZ.
2. Trigger zombie drag-down and inspect the explicit flag. Ordinary zombie
   attacks may remain unknown or show a suspected secondary mechanism; a bite
   or nearby zombie alone must not become a confirmed cause.
3. Test fire, bleeding and zombie infection separately. Compare the observed
   damage callbacks with the suspected source and its age at death.
4. Test mixed damage, such as burning while bleeding. Preserve both sources;
   the last callback must remain labelled suspected, never certain.
5. Test a vehicle-occupant crash separately from being struck by a vehicle.
   Verify the single-player event paths before making multiplayer claims.
6. Exercise cancellation/reload, a stale damage window, and repeated final
   exports. Missing recent evidence stays unknown and the first successful
   terminal snapshot remains unchanged. Check an outpost/landmark and an
   unregistered location, including a nonzero floor or basement when possible.
7. Submit the final export locally, inspect terminal evidence, and approve it.
   Confirm normalized values appear only after approval. This does not require
   publishing a Workshop update or modifying hosted DEV data.

## Status definitions

- 🟢 **Implemented**: TGSRR already collects or persists the underlying canonical information. This does not by itself mean the final submission exporter is complete.
- 🔵 **In progress - awaiting decision**: the technical collection/export
  infrastructure exists, but an agreed content or policy decision is still
  required before the contract can be activated and considered complete.
- 🟡 **Planned**: accepted into the export contract, with a sufficiently clear intended meaning, but collection or persistence is incomplete.
- 🔴 **Needs investigation**: desired data whose authoritative Project Zomboid event path, attribution, performance model, or precise gameplay definition must be established before implementation is promised.
- ⚪ **Deferred**: intentionally excluded from the current export scope because
  its value does not presently justify its ambiguity or implementation cost.

## Export data

The `Contract` scope contains the agreed export contract. `Team request` contains additional desired data not already represented by a contract row.

| Scope | Data | Status | Notes |
|---|---|---|---|
| Team request | Death location and initial cause evidence | 🟢 Implemented | 42.22 records optional terminal XYZ/building/registered location, fatal-fall and drag-down flags, and the latest observation per recent damage source. Explicit flags take priority; otherwise the last source within ten real-time seconds is only suspected. One schema-1 snapshot is bound to the terminal event and projection, validated on import and normalized on approval. Missing older evidence remains unknown. In-game event ordering and coverage validation remain outstanding; see the first-slice checklist above. |
| Team request | Daily and run-wide outdoor temperature extremes | 🟢 Implemented | `outdoorTemperature` carries sampled minimum/maximum Celsius and each observation's UTC, world age, time of day and one-based calendar date. Global outdoor weather is sampled at initialization and every game minute regardless of player location. Completed days seal their extremes; the projection includes active-day and independent run-wide records. Existing history is partial, ties preserve first occurrence and old omissions remain unknown. Desktop collection and export round trips pass; website approval normalizes the data and presents a temperature chart. In-game verification remains outstanding. |
| Contract | Character name | 🟢 Implemented | Starting and current character metadata are captured; the name is presentation metadata, not the run identity. |
| Contract | Occupation | 🟢 Implemented | The raw Project Zomboid profession ID is captured immutably in `character.starting.professionId` and observed again in `character.current.professionId`. Localized occupation names are left to the website. |
| Contract | Starting traits | 🟢 Implemented | Raw namespaced trait IDs are captured from the selected-traits list before the character-creation transition and persisted immutably for the matching new character. Bootstrapped or missed captures are explicitly marked partial. Spawned effective traits are retained separately. |
| Contract | Current traits | 🟢 Implemented | Format-3 exports contain the current sorted effective trait-ID set; the website derives additions, removals, and cross-run population comparisons. |
| Contract | Run start date and time | 🟢 Implemented | Stored with the immutable TGSRR run identity. |
| Contract | Starting location | 🟢 Implemented | Before world initialization, `character.chosenStartingRegion` captures explicit or blind-random selection, the resolved raw PZ region ID, and UTC. Run creation separately captures immutable integer XYZ, the precision-safe BuildingDef ID when present, UTC, and world age in `character.startingLocation`. Existing-save observations are marked partial and do not claim to be the original spawn. Town interpretation belongs to the website. |
| Contract | Timestamp for the beginning of each survived day | 🟢 Implemented | A hash-chained `day.started` event records UTC, world age, calendar date, and the survived-day index. The first observation is marked partial when an existing run is bootstrapped. |
| Contract | Total zombie kills | 🟢 Implemented | Uses the authoritative Character Info total. |
| Contract | Daily zombie-kill totals | 🟢 Implemented | Each `day.started` event seals the preceding day's delta from authoritative Character Info kill totals. Format-3 also exports the active unfinished day's live delta without mutating history. |
| Team request | Current and daily body weight | 🟢 Implemented | Current Nutrition weight remains `weight.currentKilograms`. New active and completed days also retain measured `weightKilograms`, alongside signed `weightDeltaKilograms`. Older missing absolute weights remain unknown; omitted deltas still mean zero. Website approval stores observations in nullable `RunDailyRecord.weight_kilograms`. |
| Contract | Kills with each weapon | 🟢 Implemented | TGSRR attributes player-credited deaths using the actual hit weapon and credited attacker. Format-3 exports cumulative ID-sorted totals and active-day deltas keyed by full item type or `__VEHICLE__`, `__UNARMED__`, and `__UNKNOWN__`. Vanilla does not credit delayed fire deaths to the player. Existing runs disclose a partial baseline. |
| Team request | Zombies killed by fire | 🟢 Implemented | Tracked separately from vanilla and weapon kills because ongoing fire clears `attackedBy` and does not increment player kills. Format-3 exports cumulative and active-day fire-death counts with partial-baseline disclosure. |
| Team request | Zombie kill posture and fence/window assists | 🟢 Implemented | Player-credited deaths are classified cumulatively as `standing`, `onfront`, `onback`, `fenceAssist`, or `windowAssist`. Fence/window traversal is tagged transiently in zombie ModData and remains eligible while the zombie is prone or getting up; standing recovery clears it. Assist classifications override ordinary death posture. Existing runs disclose a partial baseline. No daily delta is recorded. |
| Contract | Current level and XP for every skill | 🟢 Implemented | Format-3 exports every registered non-category perk as a stable, ID-sorted record containing category ID, current level, and cumulative XP. Localized names are intentionally excluded. |
| Contract | Daily and total XP gained for every skill | 🟢 Implemented | Day-boundary snapshots use stable perk IDs and seal non-zero XP deltas for the preceding day. Format-3 includes the active unfinished day's non-zero deltas, while total gain remains derivable without recording every `AddXP`. |
| Contract | Locations visited and when | 🟢 Implemented | The versioned registry defines 21 optional landmarks, including multi-BuildingDef sites. First physical entry appends one `location.visited` event with stable location and BuildingDef IDs, discovery method, UTC, world age, and coordinates. Format-3 schema-1 exports every registered landmark and its first-visit state; older registry histories are marked partial. The separate all-building reconciliation registry is intentionally not exported. |
| Contract | Towns visited and when | 🟢 Implemented | A TGSRR-owned registry defines stable town IDs and one or more map-reviewed activation points per settlement. Per-point radii range from 200 tiles for compact towns to 350 for Louisville coverage. First entry appends one `town.visited` event and permanently stores its UTC time, world age, triggering point ID, and player coordinates. Format-3 exports every registered town and its first-visit state; runs bootstrapped on an existing game save are marked partial. |
| Contract | Skill books and recipe magazines read and when | 🟢 Implemented | Run initialization records one sorted `literature.baseline` containing only completed PZ literature with a registered `SkillBook` entry or one or more learned recipes. Successful local-player `ISReadABook.complete()` transitions append `literature.read` only for those categories, carrying full item ID, `skill_book`/`recipe_literature` classification, learned recipe IDs, UTC, and world age. Leisure books, ordinary magazines, newspapers, crosswords, and generic print media are excluded. Format-3 exports the filtered baseline and per-item completion summaries; runs bootstrapped on an existing game save remain partial. |
| Contract | Progress for every outpost | 🟢 Implemented | Format-3 sparsely exports outposts and deliverables carrying non-default state or retained evidence. The registry version defines omitted members as undiscovered and incomplete; website approval expands them into all 13 outposts and 169 deliverables. |
| Contract | Completed outposts and completion order | 🟢 Implemented | Format-3 derives an immutable first-completion list from the sole hash-chained `outpost.completed` event per outpost. Projection schema 2 provides bounded first/latest completion, latest regression, completion/regression counts, and current state. Later transitions update the summary without adding ledger events. Sparse omission means the versioned catalogue default. |
| Contract | Kill milestones and elapsed days | 🟢 Implemented | Format-3 exports every hash-chained `kills.milestone.reached` event in sequence order with threshold, observed kill total, character ID, UTC, world age, and elapsed days since run creation. |
| Contract | Skill milestones, including level 10 and elapsed days | 🟢 Implemented | The first existing `skill.level.reached` event at exactly level 10 for each stable skill ID becomes its milestone. Format-3 exports skill/category IDs, level, chronological completion order, event sequence, UTC, world age, and elapsed days. Levels 1-9 are not milestones, duplicate level-10 events cannot replace the first, and bootstrapped runs disclose partial history. |
| Contract | Outpost milestones and elapsed days | 🟢 Implemented | Format-3 exports the first completion of each outpost deliverable with stable IDs, observed value, event sequence, UTC, world age, and elapsed days. Later completions and regressions update bounded counts and latest observations without adding ledger events. Only non-default outpost and deliverable evidence is exported; the website expands catalogue omissions. |
| Contract | Overall challenge progress | 🟢 Implemented | Format-3 exports a rules-versioned map of the Tracker's kills, skills, and outposts summaries. Each retains current, target, normalized progress, availability, and status. No single overall percentage is defined. |
| Contract | Challenge mode | 🟢 Implemented | Every format-3 schema-1 projection contains `challenge.id` and `challenge.gameMode`. PZ may clear `Core.challengeId` before tracker startup. Each TGSRR Last Stand file therefore registers its own canonical ID and exact game-mode pair while defining the challenge; Identity resolves the live game mode against those authoritative definitions, with `LastStandData.chosenChallenge` and live Core evidence retained as compatible fallbacks, then persists the first successful observation. Known IDs are `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`; unknown evidence is retained without fuzzy matching. |
| Contract | Whether the run remains official | 🔵 In progress - awaiting decision | Run eligibility is website/moderator-owned. The mod will export neutral rule-relevant evidence rather than an authoritative official/unofficial verdict; the complete evidence and policy boundary are still being defined. |
| Contract | Save rollbacks and recovery decisions | 🟢 Implemented | Crash-interrupted session commits are automatically reconciled only when the verified ahead tail contains safe session/recovery records and the independent session-log cursor agrees; their decision authority is `{ type = "system", id = "tgsrr" }`. A verified ahead gameplay tail pauses play for an explicit player decision. Continuing creates or idempotently resumes a new ledger epoch from the restored checkpoint while preserving the old tail and its metadata immutably. Format-3 exports neutral recovery status, active epoch, decision records, and complete superseded event bodies. Accepted totals follow only the active branch; approval and eligibility consequences belong to the website/moderator. |
| Team request | Power-cut calendar/world-age reconciliation | 🟢 Implemented | Two alternating checksummed local clock checkpoints are written only after `OnPostSave` and bind the saved event cursor to calendar, time of day, nights survived, world age, and character hours survived. A matching cursor plus non-regressed character hours independently reconstructs the expected clock. Declared gameplay-rollback recovery explicitly skips reconciliation so the recovered branch retains its loaded clock and establishes a fresh anchor on its next save. On eligible loads, matching clocks are a read-only no-op; disagreement pauses before session recording and requires explicit repair or stops tracking. Applied repairs append `run.clock.repaired` evidence, while raw checkpoints remain outside the export. |
| Contract | Mods used when the run began | 🟢 Implemented | Captures Mod IDs, Workshop IDs, and their mapping. |
| Contract | Mods added or removed during later sessions | 🟢 Implemented | Session-start deltas are recorded, and format-3 also exports the current sorted Mod ID/Workshop ID mapping so consumers need not reconstruct the active state from history. |
| Team request | Distance travelled | 🟢 Implemented | Constant-memory tick sampling records on-foot and driving planar metres, total distance and rejected teleport-sized steps. No route history. Vehicle/role changes, reloads and long gaps reset the baseline. Cumulative and daily values export and normalize on approval; old mode coverage remains partial/unknown. Mode separation, reload and rollover verified in game; measured-route accuracy remains pending. |
| Team request | Animals slaughtered | 🟢 Implemented | TGSRR wraps the successful Build 42 `ISKillAnimal.complete()` and `ISKillAnimalInInventory.complete()` actions for the local player. It records Project Zomboid's raw `IsoAnimal:getAnimalType()` value, a cumulative total, cumulative totals per animal type, and daily deltas per type. Killing an animal through ordinary combat and processing an already-dead carcass are not counted as slaughter. Individual slaughters are deliberately not ledger events, keeping export growth bounded by survived days and observed animal types. Existing runs are partial. |
| Team request | Animals trapped | 🟢 Implemented | TGSRR wraps successful local-player `ISCheckTrapAction.complete()` claims and requires the trap to contain an animal before completion. It preserves PZ's raw trap-animal category (`rabbit`, `squirrel`, `bird`, `mouse`, `rat`, or `raccoon`) and full trap item ID. Format-3 exports the cumulative total plus aggregates by animal category, trap ID, and animal/trap pairing; active and completed days contain pairing deltas from which either dimension can be derived. Individual catches are deliberately not ledger events. Existing runs are partial. |
| Team request | Domestic animal births | 🟢 Implemented | PZ has no Lua birth event: unloaded husbandry advances pregnancy but creates the litter only after the mother returns to loaded server simulation. TGSRR reconciles loaded cell, connected-hutch, and animal-trailer populations every five seconds. It assigns TGSRR-owned identities in animal ModData, baselines existing animals, and counts only a previously untagged non-wild baby whose already-tagged mother is present or recoverably linked. Full identity bookkeeping remains internal; format-3 exports cumulative and active/completed-day totals per raw newborn animal type. Existing runs are partial. |
| Team request | XP gained through skill-book boosts | ⚪ Deferred | Direct attribution is not currently valuable enough to justify separating book boosts from traits, professions, sandbox settings, and other XP modifiers. Timestamped skill-book completion together with daily per-skill XP deltas provides sufficient website-side correlation without exporting a potentially misleading derived statistic. |
| Team request | Days survived before generator knowledge is learned | 🟢 Implemented | TGSRR observes PZ's authoritative `isRecipeActuallyKnown("Generator")` state once per second. Its first known state appends one neutral `knowledge.generator.first_observed` milestone and format-3 exports the first-observation UTC, world age, survived days, whether it was already known when tracking began, and partial-history status. Contemporaneous evidence preserves the raw profession ID, Electrical level, Inventive state, and whether `Base.ElectronicsMag4` appears in TGSRR's literature history. These are evidence hints rather than a claimed acquisition source because vanilla can grant the recipe through the magazine, the Electrician profession, or Electrical level 3 (level 2 with Inventive), and mods/admin tools can grant it too. |
| Team request | Injuries sustained | 🟢 Implemented | `OnPlayerGetDamage` reports repeated health-loss causes rather than wound creation, so TGSRR instead reconciles the local player's 17 authoritative `BodyPart` records on `OnPlayerUpdate`. False-to-true transitions count distinct injury manifestations for bite, scratch, laceration, deep wound, fracture, lodged glass, lodged bullet, and burn. Format-3 exports cumulative totals by type, body part, and type/body-part pairing plus active/completed-day pairing deltas. Bleeding and wound infection are complications rather than separately counted injuries. PZ exposes no wound identity, so another strike into an already-active injury of the same type and body part cannot be counted reliably; existing runs are partial. |
| Team request | Zombie-caused injuries | 🟢 Implemented | Each newly observed injury transition is additionally classified as `zombieAssociated` only when the player's contemporaneous `attackedBy` object is a zombie whose `AttackDidDamage` flag remains true. Format-3 exports separate cumulative and daily aggregates by injury type and body part. The label deliberately describes strong contemporaneous evidence rather than guaranteed causation because PZ retains no durable wound-source field and `attackedBy` can otherwise become stale. |
| Team request | Milk collected | 🟢 Implemented | TGSRR wraps Build 42.20's incremental `ISMilkAnimal:milk()` edge and measures the authoritative animal milk-quantity decrease around each original call. This preserves transfers smaller than the nominal 0.1-litre tick when vessel capacity or carried weight constrains the Java transfer, while excluding aborted ticks, no-capacity attempts, and milk later spilled by animal stress. Format-3 exports cumulative and active/completed-day litres by raw milk fluid ID. Individual transfers are not ledger events; existing runs are partial. |
| Team request | Butter produced | 🟢 Implemented | Build 42.20 has one vanilla production recipe: `Base.churn_butter` consumes 5 litres of cow/sheep-milk mixture and creates one `Base.Butter`. Although opened from the Butter Churn entity, its vanilla UI executes through `ISWidgetHandCraftControl`, not `ISWidgetCraftLogicControl`; `ISHandcraftAction:performRecipe()` creates and awards the output before the control's completion callback. TGSRR pairs the local player's action-start callback with completion or cancellation, counting one butter only on completion. Exports contain cumulative plus active/completed-day counts; existing runs are partial. |
| Team request | Fish caught | 🟢 Implemented | TGSRR captures the local player's Build 42 fishing result when vanilla creates `ISPickupFishAction` for the landed item. Only results carrying vanilla's fish hand-item marker count; fishing trash and unattended fishing-net catches are excluded. A fish still counts if pickup is interrupted because vanilla drops that already-landed fish at the player's feet. Format-3 exports a cumulative total, stable full-item-ID totals, and active/completed-day ID deltas. Dynamic localized size names are excluded; existing runs are partial. |
| Team request | Animals petted | 🟢 Implemented | TGSRR wraps successful local-player `ISPetAnimal:complete()` calls and exports an independently authoritative cumulative total plus totals and daily deltas by PZ's raw animal type. This measures completed petting actions, not whether the animal or player received a cooldown-limited mechanical benefit. Individual pets are not ledger events, and existing runs disclose partial history. |
| Team request | Fluid consumed by type | 🟢 Implemented | TGSRR measures authoritative container/world-source before-and-after amounts for manual local-player drinking and exports independently authoritative cumulative litres plus daily deltas by raw fluid type. Mixtures are explicitly classified as `__MIXED__`. Individual sips are not ledger events, and existing runs disclose partial history. |
| Team request | Calories consumed | 🟢 Implemented | TGSRR accumulates calories actually applied by completed or partially applied local-player food and fluid consumption. It exports an independently authoritative cumulative value plus daily deltas. It deliberately does not measure net Nutrition balance, which metabolism changes continuously and Java clamps. Individual meals are not ledger events, and existing runs disclose partial history. |
| Team request | Hunger fulfilled | ⚪ Deferred | Satiety supplied is distinct from calories and can come from both foods and fluids, but it substantially overlaps the accepted calorie-consumption statistic and is less useful as a standalone comparison. Do not infer it from ordinary hunger decreases until the team identifies a concrete scoring or presentation use. |
| Team request | Generator repairs | 🟢 Implemented | TGSRR wraps each successful local-player `ISFixGenerator:complete()` action and exports independently authoritative cumulative and daily repair counts plus actual condition restored. Individual repairs are not ledger events, and existing runs disclose partial history. |
| Team request | Weapons broken | 🟢 Implemented | TGSRR follows the Build 42 dual path established by Twist Stats: wrap weapon `OnBreak` callbacks and briefly observe condition after `OnWeaponSwing` for weapons without a callback. Weak item-reference deduplication prevents both paths counting the same break. Format-3 exports cumulative ID-sorted totals and active-day deltas, while each `day.started` event seals the preceding daily aggregate. Individual breaks are deliberately not appended to the ledger, keeping long-run growth bounded by survived days and weapon types. Existing runs are partial. |
| Team request | Real time spent in nimble stance | 🟢 Implemented | The export contains independently authoritative cumulative and daily real elapsed movement milliseconds while the local player moves on foot with `isAiming()`. Standing aim, vehicles, pause/loading gaps, and `FishingState` are excluded. Bootstrapped runs disclose a partial baseline. |
| Team request | Real time spent in the run/stream | 🟢 Implemented | The export contains independently authoritative cumulative and daily active-gameplay milliseconds. Pause and loading gaps are excluded. This measures active run time, not whether broadcasting software was live. Bootstrapped runs disclose a partial baseline. |

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
  `outpost.completed` records. Compact rolled-over `day.started` records contain
  `completedDay` with only non-zero scalar deltas and non-empty delta maps;
  missing delta fields canonically mean zero.
- A session started with Project Zomboid debug mode enabled logs that state and
  appends one timestamped `run.debug.enabled` event. The complete verified
  ledger carries this neutral evidence into format-3 exports without declaring
  the run invalid.
- The outpost progress store separately persists the latest observation for every
  deliverable and the data required to derive current outpost completion.
- Format-3 currently exports the complete verified event ledger plus a comprehensive live
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
- Domestic births use conservative five-second population reconciliation because
  PZ exposes no birth event. Existing animals receive persistent TGSRR identities
  without being counted; only a new non-wild baby linked to a previously known
  mother increments cumulative and daily raw-type aggregates. Identity records
  are collector bookkeeping and are not exported.
- Character death appends one hash-chained `run.ended` event with
  `reason = deceased`. The export projection repeats the resulting `deceased`
  lifecycle and terminal event cursor for convenient website display and
  readback verification. Death automatically generates the final export, while
  the post-death button permits a deliberate replacement export. Submission
  status and run eligibility remain website-owned policy fields.
