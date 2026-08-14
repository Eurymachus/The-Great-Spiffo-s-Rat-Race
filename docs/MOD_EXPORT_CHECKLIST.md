# Mod: Export Data Checklist

## Purpose

This is the working checklist for the player/run data that TGSRR intends to collect and ultimately include in a Rat Race export. Update the status and implementation notes as collectors, persistence, integrity handling, and export serialization are completed.

TGSRR is always the sole authority for this data. Installed unrelated mods do not supply, replace, or alter any item in this checklist. The Tracker is TGSRR's player-facing presentation of the canonical state.

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
| Contract | Character name | 🟢 Implemented | Starting and current character metadata are captured; the name is presentation metadata, not the run identity. |
| Contract | Occupation | 🟢 Implemented | The raw Project Zomboid profession ID is captured immutably in `character.starting.professionId` and observed again in `character.current.professionId`. Localized occupation names are left to the website. |
| Contract | Starting traits | 🟢 Implemented | Raw namespaced trait IDs are captured from the selected-traits list before the character-creation transition and persisted immutably for the matching new character. Bootstrapped or missed captures are explicitly marked partial. Spawned effective traits are retained separately. |
| Contract | Current traits | 🟢 Implemented | Format-3 exports contain the current sorted effective trait-ID set; the website derives additions, removals, and cross-run population comparisons. |
| Contract | Run start date and time | 🟢 Implemented | Stored with the immutable TGSRR run identity. |
| Contract | Timestamp for the beginning of each survived day | 🟢 Implemented | A hash-chained `day.started` event records UTC, world age, calendar date, and the survived-day index. The first observation is marked partial when an existing run is bootstrapped. |
| Contract | Total zombie kills | 🟢 Implemented | Uses the authoritative Character Info total. |
| Contract | Daily zombie-kill totals | 🟢 Implemented | Each `day.started` event seals the preceding day's delta from authoritative Character Info kill totals. Format-3 also exports the active unfinished day's live delta without mutating history. |
| Team request | Current and daily body weight | 🟢 Implemented | Format-3 exports the current Nutrition weight in kilograms. The active-day projection contains its signed change from the day baseline, and each compact `day.started.completedDay` seals the preceding day's signed `weightDeltaKilograms`; a missing completed-day delta means zero. |
| Contract | Kills with each weapon | 🟢 Implemented | TGSRR attributes player-credited deaths using the actual hit weapon and credited attacker. Format-3 exports cumulative ID-sorted totals and active-day deltas keyed by full item type or `__VEHICLE__`, `__UNARMED__`, and `__UNKNOWN__`. Vanilla does not credit delayed fire deaths to the player. Existing runs disclose a partial baseline. |
| Team request | Zombies killed by fire | 🟢 Implemented | Tracked separately from vanilla and weapon kills because ongoing fire clears `attackedBy` and does not increment player kills. Format-3 exports cumulative and active-day fire-death counts with partial-baseline disclosure. |
| Team request | Zombie kill posture and fence/window assists | 🟢 Implemented | Player-credited deaths are classified cumulatively as `standing`, `onfront`, `onback`, `fenceAssist`, or `windowAssist`. Fence/window traversal is tagged transiently in zombie ModData and remains eligible while the zombie is prone or getting up; standing recovery clears it. Assist classifications override ordinary death posture. Existing runs disclose a partial baseline. No daily delta is recorded. |
| Contract | Current level and XP for every skill | 🟢 Implemented | Format-3 exports every registered non-category perk as a stable, ID-sorted record containing category ID, current level, and cumulative XP. Localized names are intentionally excluded. |
| Contract | Daily and total XP gained for every skill | 🟢 Implemented | Day-boundary snapshots use stable perk IDs and seal non-zero XP deltas for the preceding day. Format-3 includes the active unfinished day's non-zero deltas, while total gain remains derivable without recording every `AddXP`. |
| Contract | Locations visited and when | 🟢 Implemented | The versioned registry defines 21 optional landmarks, including multi-BuildingDef sites. First physical entry appends one `location.visited` event with stable location and BuildingDef IDs, discovery method, UTC, world age, and coordinates. Format-3 schema-1 exports every registered landmark and its first-visit state; older registry histories are marked partial. The separate all-building reconciliation registry is intentionally not exported. |
| Contract | Towns visited and when | 🟢 Implemented | A TGSRR-owned registry defines stable town IDs and one or more map-reviewed activation points per settlement. Per-point radii range from 200 tiles for compact towns to 350 for Louisville coverage. First entry appends one `town.visited` event and permanently stores its UTC time, world age, triggering point ID, and player coordinates. Format-3 exports every registered town and its first-visit state; runs bootstrapped on an existing game save are marked partial. |
| Contract | Skill books and recipe magazines read and when | 🟢 Implemented | Run initialization records one sorted `literature.baseline` containing only completed PZ literature with a registered `SkillBook` entry or one or more learned recipes. Successful local-player `ISReadABook.complete()` transitions append `literature.read` only for those categories, carrying full item ID, `skill_book`/`recipe_literature` classification, learned recipe IDs, UTC, and world age. Leisure books, ordinary magazines, newspapers, crosswords, and generic print media are excluded. Format-3 exports the filtered baseline and per-item completion summaries; runs bootstrapped on an existing game save remain partial. |
| Contract | Progress for every outpost | 🟢 Implemented | Format-3 exports all 13 stable outpost IDs with discovery/stage state, strict completion, weighted progress, requirement counts, timestamps, and every latest persisted deliverable value. |
| Contract | Completed outposts and completion order | 🟢 Implemented | Format-3 derives an immutable first-completion list from the hash-chained `outpost.completed` events. Each entry includes its chronological completion order, event sequence, UTC, world age, elapsed days since run creation, and requirement totals. Later regression and re-completion do not replace the first completion; bootstrapped runs mark the milestone projection partial. |
| Contract | Kill milestones and elapsed days | 🟢 Implemented | Format-3 exports every hash-chained `kills.milestone.reached` event in sequence order with threshold, observed kill total, character ID, UTC, world age, and elapsed days since run creation. |
| Contract | Skill milestones, including level 10 and elapsed days | 🟢 Implemented | The first existing `skill.level.reached` event at exactly level 10 for each stable skill ID becomes its milestone. Format-3 exports skill/category IDs, level, chronological completion order, event sequence, UTC, world age, and elapsed days. Levels 1-9 are not milestones, duplicate level-10 events cannot replace the first, and bootstrapped runs disclose partial history. |
| Contract | Outpost milestones and elapsed days | 🟢 Implemented | Format-3 exports the first completion of each outpost deliverable with stable outpost/deliverable IDs, observed value, event sequence, UTC, world age, and elapsed days. Whole-outpost milestones are represented by the ordered completion projection. |
| Contract | Overall challenge progress | 🟢 Implemented | Format-3 exports a rules-versioned map of the Tracker's kills, skills, and outposts summaries. Each retains current, target, normalized progress, availability, and status. No single overall percentage is defined. |
| Contract | Challenge mode | 🟢 Implemented | Every format-3 schema-1 projection contains `challenge.id` and `challenge.gameMode`. PZ may clear `Core.challengeId` before tracker startup. Each TGSRR Last Stand file therefore registers its own canonical ID and exact game-mode pair while defining the challenge; Identity resolves the live game mode against those authoritative definitions, with `LastStandData.chosenChallenge` and live Core evidence retained as compatible fallbacks, then persists the first successful observation. Known IDs are `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`; unknown evidence is retained without fuzzy matching. |
| Contract | Whether the run remains official | 🔵 In progress - awaiting decision | Run eligibility is website/moderator-owned. The mod will export neutral rule-relevant evidence rather than an authoritative official/unofficial verdict; the complete evidence and policy boundary are still being defined. |
| Contract | Save rollbacks and recovery decisions | 🟢 Implemented | Crash-interrupted session commits are automatically reconciled only when the verified ahead tail contains safe session/recovery records and the independent session-log cursor agrees; their decision authority is `{ type = "system", id = "tgsrr" }`. A verified ahead gameplay tail pauses play for an explicit player decision. Continuing creates or idempotently resumes a new ledger epoch from the restored checkpoint while preserving the old tail and its metadata immutably. Format-3 exports neutral recovery status, active epoch, decision records, and complete superseded event bodies. Accepted totals follow only the active branch; approval and eligibility consequences belong to the website/moderator. |
| Team request | Power-cut calendar/world-age reconciliation | 🟢 Implemented | Two alternating checksummed local clock checkpoints are written only after `OnPostSave` and bind the saved event cursor to calendar, time of day, nights survived, world age, and character hours survived. A matching cursor plus non-regressed character hours independently reconstructs the expected clock. Declared gameplay-rollback recovery explicitly skips reconciliation so the recovered branch retains its loaded clock and establishes a fresh anchor on its next save. On eligible loads, matching clocks are a read-only no-op; disagreement pauses before session recording and requires explicit repair or stops tracking. Applied repairs append `run.clock.repaired` evidence, while raw checkpoints remain outside the export. |
| Contract | Mods used when the run began | 🟢 Implemented | Captures Mod IDs, Workshop IDs, and their mapping. |
| Contract | Mods added or removed during later sessions | 🟢 Implemented | Session-start deltas are recorded, and format-3 also exports the current sorted Mod ID/Workshop ID mapping so consumers need not reconstruct the active state from history. |
| Team request | Distance travelled | 🟢 Implemented | TGSRR follows the established `OnPlayerMove` planar-coordinate pattern used by Twist Stats, treating one world unit as one metre and including vehicle travel. It persists only a monotonic cumulative aggregate, not raw positions. A real-time speed/step bound rejects load jumps and teleports while counting rejected samples. Format-3 exports cumulative metres plus the active day's metre delta; each `day.started` event seals the preceding daily delta. Existing runs are partial. |
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
| Team request | Animals petted | 🟢 Implemented | TGSRR wraps successful local-player `ISPetAnimal:complete()` calls and exports a cumulative total plus totals by PZ's raw animal type. This measures completed petting actions, not whether the animal or player received a cooldown-limited mechanical benefit: `IsoAnimal:petAnimal()` still calls `IsoPlayer:petAnimal()` when the animal's own pet timer blocks stress, acceptance, or Husbandry gains, and the player's benefit has a separate one-hour calendar cooldown. Individual pets are not ledger events, no daily delta is recorded, and existing runs disclose partial history. |
| Team request | Fluid consumed by type | 🟢 Implemented | TGSRR measures authoritative container/world-source before-and-after amounts for manual local-player drinking and exports cumulative litres by raw fluid type. Mixtures are explicitly classified as `__MIXED__` because Build 42.20 does not publicly enumerate a container's component instances. Java `autoDrink()` has only a cancellation hook, so TGSRR instead retains the single Java-selected eligible water-container reference and correlates its amount loss with authoritative thirst reduction; manual observations refresh that reference to prevent double-counting. Java source selection is refreshed at most once per second or when the retained source is depleted, avoiding continuous full-inventory scans. Individual sips are not ledger events, no daily delta is recorded, and existing runs disclose partial history. |
| Team request | Calories consumed | 🟢 Implemented | TGSRR accumulates calories actually applied by completed or partially applied local-player food and fluid consumption. Food calculations mirror `IsoGameCharacter:Eat()` percentage normalization and the one-fifth burnt-food rule. Fluid property calories are already scaled to the container's current amount, so the collector applies the authoritative removed-volume fraction. It deliberately does not measure net Nutrition balance, which metabolism changes continuously and Java clamps. Individual meals are not ledger events, no daily delta is recorded, and existing runs disclose partial history. |
| Team request | Hunger fulfilled | ⚪ Deferred | Satiety supplied is distinct from calories and can come from both foods and fluids, but it substantially overlaps the accepted calorie-consumption statistic and is less useful as a standalone comparison. Do not infer it from ordinary hunger decreases until the team identifies a concrete scoring or presentation use. |
| Team request | Generator repairs | 🟢 Implemented | TGSRR wraps each successful local-player `ISFixGenerator:complete()` action, meaning one electronics scrap was consumed, and exports both the cumulative repair count and authoritative before/after condition restored. One menu command may queue several repairs, so each completed scrap-consuming action counts separately. Measuring the generator delta captures the final repair's clamp at 100 rather than assuming the nominal `4 + Electrical level / 2`. Individual repairs are not ledger events, no daily delta is recorded, and existing runs disclose partial history. |
| Team request | Weapons broken | 🟢 Implemented | TGSRR follows the Build 42 dual path established by Twist Stats: wrap weapon `OnBreak` callbacks and briefly observe condition after `OnWeaponSwing` for weapons without a callback. Weak item-reference deduplication prevents both paths counting the same break. Format-3 exports cumulative ID-sorted totals and active-day deltas, while each `day.started` event seals the preceding daily aggregate. Individual breaks are deliberately not appended to the ledger, keeping long-run growth bounded by survived days and weapon types. Existing runs are partial. |
| Team request | Real time spent in nimble stance | 🟢 Implemented | Format-3 exports cumulative real elapsed `nimbleStance.movementMilliseconds` while the local player moves on foot with `isAiming()`. Standing aim, vehicles, pause/loading gaps, and `FishingState` are excluded. Gaps over one second are discarded rather than inferred. Bootstrapped runs disclose a partial baseline. No daily delta is recorded. |
| Team request | Real time spent in the run/stream | 🟢 Implemented | Format-3 exports cumulative `activeGameplay.milliseconds` using a Twist Stats-style wall clock. The visible in-game pause menu, `isGamePaused()`, and either game-speed source reporting zero suspend accumulation; loading/hitch gaps over five seconds are discarded. Time acceleration still counts real time. Bootstrapped runs disclose a partial baseline. This measures active run time, not whether broadcasting software was live. No daily delta is recorded. |

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
