# Mod: Run Data

## Goal

Build a stable, exportable record for one Rat Race ironman run.

TGSRR is always the sole authority for collection, persistence, normalization, and export. Its behaviour and exported data do not change when unrelated mods are installed. Other mods may be studied as read-only implementation references, but TGSRR does not read their state, mirror their storage, select them as authorities, or hand collection to them.

See [MOD_REFERENCE_DATA_COLLECTORS.md](MOD_REFERENCE_DATA_COLLECTORS.md) for the source audit.

Use [MOD_EXPORT_CHECKLIST.md](MOD_EXPORT_CHECKLIST.md) as the live implementation/status checklist for the agreed export contract and additional team requests.

## Requested data

- Timestamp at which each survivor day began.
- Starting character forename, surname, and combined display name.
- Daily zombie-kill deltas.
- Daily XP deltas per internal skill ID.
- Locations visited and visit times.
- Towns visited and visit times.
- Skill books and recipe magazines read and read times.
- Starting trait IDs.
- Current trait IDs.
- Kills by full weapon item ID.
- Loaded mod ID / Workshop ID mappings at run start and timestamped added/removed deltas for both identifier sets at every later session start.

Kills, current skill state, and outpost deliverables remain existing normalized challenge capabilities and are not duplicated into every history event.

## Identifier policy

Persist stable identifiers, not localized display values:

- Run identity: TGSRR-owned world/run ID; never derived solely from the character name.
- Character identity: exported starting forename, surname, and display name as metadata associated with the TGSRR run ID.
- Skills: internal perk ID.
- Traits: namespaced character-trait ID where available.
- Literature and weapons: full item type, including module.
- Towns: stable TGSRR-owned town ID. A town may have multiple activation points,
  but all points resolve to the same permanent visit identity.
- Locations: registered location ID, plus coordinates/world context where the record requires it.
- Mods: paired activated mod ID and Workshop ID where available. Workshop ID is the website's external lookup/link key; mod ID remains required because one Workshop item may contain multiple mods and local/unpublished mods have no Workshop ID.

The website maps these IDs to names, icons, categories, aliases, and game-version applicability. Those mappings can be maintained by a Zomboid Integration role without rewriting historical exports.

The character name is intentionally exported for participant/run presentation, but it is not an identity key: names are mutable and non-unique. The run header captures the starting name, and later name changes, if supported or observed, should be recorded as timestamped metadata changes without changing the run ID.

## Time policy

Historical records should carry authoritative game time and optional real time:

```lua
time = {
    worldAgeHours = number,
    survivorDay = number,
    gameYear = number,
    gameMonth = number,
    gameDay = number,
    gameHour = number,
    gameMinute = number,
    utcSeconds = number,
}
```

World age/survivor time orders the run even when the system clock changes. UTC time supports stream/session correlation. Fields unavailable at a particular lifecycle hook may be omitted rather than invented.

## Collector model

TGSRR collectors are always registered for Rat Race runs. They use Project Zomboid events where reliable, compact in-memory aggregates for high-frequency activity, and controlled file flushes at lifecycle boundaries. No collector tests for or consumes another mod's state.

- Daily kill and per-skill XP deltas: TGSRR counters accumulated from authoritative game events and sealed at the day boundary.
- Starting and current traits: TGSRR ID snapshots from the Build 42 character trait registry.
- Weapon kills: TGSRR attributes player-credited zombie deaths from the actual
  `OnWeaponHitCharacter` weapon and the `OnZombieDead` credited attacker.
  Aggregate counters use full item type plus TGSRR pseudo IDs for vehicle,
  unarmed, and otherwise unknown sources. Delayed fire deaths are excluded
  because vanilla clears `attackedBy` and does not increment the player's zombie
  kill counter. Completed days seal source deltas; the current export includes
  cumulative and active-day values.
- Zombie fire deaths: counted separately when ongoing fire kills a zombie
  without vanilla player credit. Cumulative and daily values never contribute
  to authoritative player or weapon-kill totals.
- Town visits: TGSRR checks a compact registry of map-reviewed settlement
  activation points once per real-time second. Entering any point's configured
  radius records the town's first visit as a hash-chained `town.visited` event
  and persists its UTC
  time, world age, triggering point ID, and observed player coordinates.
  Per-point radii range from 200 tiles for compact towns to 350 tiles across
  Louisville. Additional points cover large or elongated settlements without pretending
  that vanilla `TownZone` fragments form authoritative municipal boundaries.
  Hog Wallow Military Base is intentionally excluded because it is a location,
  not a town.
- Skill-literature completion: run initialization enumerates PZ's persisted
  completed-page and `AlreadyReadBook` state, filtered to items registered in
  `SkillBook` or carrying one or more learned recipes, into one immutable
  `literature.baseline`. TGSRR wraps the successful local-player
  `ISReadABook.complete()` edge and appends one `literature.read` delta carrying
  the full item ID, `skill_book`/`recipe_literature` classification, learned
  recipe IDs, UTC, and world age. Leisure books, ordinary magazines,
  newspapers, crosswords, and generic print media are excluded.
- Generator knowledge: TGSRR polls the stable vanilla recipe-knowledge query
  for raw recipe ID `Generator`. The first observed known state is persisted and
  appended once as `knowledge.generator.first_observed`, including UTC, world
  age, survived days, known-at-tracking-start and partial-history flags.
  The event and current-state snapshot also preserve contemporaneous raw
  profession ID, Electrical level, Inventive state, and whether
  `Base.ElectronicsMag4` appears in TGSRR's literature history. Those fields are
  neutral evidence rather than a declared source: vanilla can grant generator
  knowledge through that magazine, the Electrician profession, or Electrical
  level 3 (level 2 with Inventive), while mods or admin tools can add it too.
- Injuries: TGSRR reconciles the local player's 17 PZ `BodyPart` records during
  `OnPlayerUpdate`. A false-to-true transition counts one distinct manifestation
  of bite, scratch, laceration, deep wound, fracture, lodged glass, lodged
  bullet, or burn. Cumulative and daily aggregates retain both raw injury type
  and raw body-part ID. Bleeding and wound infection are complications and are
  not counted separately. PZ gives wounds no identity, so repeated damage into
  an already-active injury of the same type and body part is not reliably
  distinguishable and is not claimed.
- Zombie-associated injuries: a newly observed transition is separately
  aggregated only when the contemporaneous `attackedBy` object is a zombie and
  its `AttackDidDamage` flag is true. This is strong neutral evidence, not a
  durable source assertion: PZ stores no wound source and `attackedBy` alone can
  remain stale.
- Non-town locations: the collector and export contract are registry-driven,
  but the canonical definition list is deliberately deferred. Registry version
  0 contains no locations and exports an authoritative empty list. When the
  first definition set is approved, incrementing the registry version makes the
  existing one-second position check record permanent `location.visited` events
  with stable location/point IDs, UTC, world age, and observed coordinates.
  Runs that predate a populated registry are then marked partial automatically.
- Broken weapons use Build 42 `OnBreak` callbacks where defined and a short
  post-`OnWeaponSwing` condition check otherwise. The same item is weakly
  deduplicated across both paths. TGSRR maintains cumulative per-ID totals and
  seals daily deltas. Individual breaks are not appended to the ledger because
  their exact timestamps do not justify event growth across a multi-year run.
- Animal slaughter uses the successful local-player completion edge of Build
  42's world-animal and inventory-animal `Kill Animal` timed actions. TGSRR
  preserves the raw `IsoAnimal:getAnimalType()` value and maintains one
  cumulative run total plus cumulative and daily totals keyed by that type.
  Ordinary combat deaths and butchering an existing carcass are separate
  gameplay paths and are not counted. Individual slaughters are not ledger
  events, bounding growth by survived days and observed animal types.
- Trapped animals are counted when the local player successfully completes
  `ISCheckTrapAction` while an animal remains in the trap. This represents a
  claimed catch rather than an unattended hourly catch roll. TGSRR preserves
  both PZ's raw trap-animal category and the full trap item ID, maintaining the
  cumulative total and aggregates by category, trap, and category/trap pairing.
  Daily records retain paired deltas, allowing either dimension to be derived
  without individual catch events.
- Domestic births are reconciled from `IsoCell:getAnimals()`, animals inside
  connected hutches, and animals in loaded trailers every five seconds. PZ
  advances pregnancy during unloaded husbandry simulation but only creates the
  litter when normal loaded server updating resumes; it exposes no Lua birth
  event. TGSRR therefore assigns persistent run-owned identities in animal
  ModData, baselines existing populations, and counts only a previously
  untagged non-wild baby linked to an already-known mother. PZ animal IDs and
  mother IDs support relationship restoration but are not treated as globally
  unique identities. Identity bookkeeping is not exported; cumulative and
  daily raw newborn-type aggregates are.
- Distance travelled uses `Events.OnPlayerMove` and planar player-coordinate
  deltas, matching the established Twist Stats interpretation of one world unit
  as one metre and including vehicle movement. TGSRR adds a real-time
  speed/step bound to reject teleports and loading discontinuities, retains only
  cumulative metres and a rejected-sample count, and seals daily metre deltas.
- Day starts, visits, literature, milestones, outposts, injuries,
  production, and mod sessions: TGSRR records using their appropriate events,
  aggregates, or semantic checkpoints.

High-frequency values are not appended on every tick. TGSRR records meaningful state transitions and periodic/session/day checkpoints so the canonical history remains compact.

Book-boost-specific XP attribution is deliberately deferred. Timestamped
skill-book completion and daily per-skill XP deltas provide the useful evidence;
TGSRR does not attempt to separate book contribution from profession, trait,
sandbox, or other simultaneous XP modifiers.

## Run identity

The canonical run identity is a TGSRR-owned world-scoped ID stored in global ModData and used as the run-file directory key. It is not derived solely from the character name and is never replaced by an external identity.

The single ironman character is permanently associated with the run. Starting character names are exported as metadata. Existing saves first opened after this system is introduced are explicitly marked as bootstrapped at their first observed state.

See [MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md](MOD_DECISION_017_RUN_IDENTITY_AND_LIFECYCLE.md).

## File and ModData responsibilities

Use a run-scoped file root for growing histories. Streams should be separable and repairable rather than one giant mutable document.

Suggested streams:

- `days`: day-began timestamps and daily deltas.
- `visits`: location and town visit events.
- `literature`: books and magazines read.
- `traits`: starting and latest current ID snapshots, if a separate file projection is needed.
- `sessions`: loaded-mod snapshots/deltas and session boundaries.
- `milestones`: ledger-derived ordered outpost completions, kill milestones, and
  first outpost-deliverable completions with event sequence, UTC, world age, and
  elapsed days since run creation. Skill award policy remains separate.

Keep only compact recovery state and gameplay aggregates needed by TGSRR in ModData.

During development, run-state schemas are hard boundaries. TGSRR requires both
the current `TGSRR_Run.schemaVersion` (currently 19) and an explicit current
`contractVersion`; this prevents schema numbers previously rewritten by
development builds from masquerading as a compatible run. It does not migrate
an existing run with either marker missing or mismatched, nor does it decode
obsolete export or ledger formats. Testing
may deliberately clear both the world-scoped `TGSRR_Run` ModData and that
run ID's external `TGSRR/Runs/<runId>` directory. Loading the existing game save
after that reset creates a new current-schema run marked bootstrapped/partial.
This is suitable for rapid collector and UI testing. Authoritative lifecycle,
starting-character, recovery, and eligibility tests must use a brand-new Rat
Race challenge save.

Temporary development convenience: detecting an incompatible `TGSRR_Run`
automatically removes only that ModData entry and creates a new
bootstrapped/partial run, including in an ordinary non-debug live test. The old
external run directory is not deleted and cannot collide because the
replacement receives a new run ID. Remove this automatic reset and restore
strict rejection before the data contract is released.

Writes should be append/change based, remain off hot presentation paths, and flush at controlled lifecycle points. Runtime consumers should read hydrated RAM projections.

## File encoding and integrity model

The file format is intended to discourage casual editing and make corruption or alteration detectable. It is not treated as cryptographic proof of an unmodified client: the encoder and verifier execute on the participant's machine and can ultimately be reverse engineered.

Use a versioned binary record format rather than editable text. Each event record should contain:

- Format/schema version.
- Run ID and recovery epoch/branch ID where not inherited from its segment header.
- Monotonically increasing event sequence.
- Canonically encoded event type, time, identifiers, and payload.
- Length/framing data and a per-record corruption check.
- The preceding accepted record hash.
- A SHA-256 hash of the preceding hash plus the canonical current record.

The canonical event codec is now implemented as schema 2. Values are explicitly
type-tagged and length-framed, map keys are sorted, arrays retain their order,
and non-finite numbers or unsupported value types are rejected. SHA-256 is
implemented within TGSRR so it works in Build 42's restricted client Lua
environment, and is verified against known vectors when run tracking
initializes. This codec is the canonical content layer for the binary ledger.

IDs may be interned and numeric values delta encoded. Optional compression is permitted after canonical encoding. Base64 or XOR alone are not integrity measures and must not be presented as security.

Suggested run artifacts:

- `run.meta`: versioned run identity and format metadata.
- `sessions.log`: compact session-start diagnostics; the first entry contains
  the complete Mod ID/Workshop ID baseline and later entries contain only
  additions, removals, and changed Mod ID-to-Workshop ID associations.
- `segments/events-NNNNNN.bin`: immutable completed event segments and one appendable current segment.
- `state-current.bin`: atomically replaced canonical current-state snapshot.
- `recovery-NNNN.bin`: immutable recovery evidence/authorization segments where needed.
- `run.export`: generated submission envelope containing the data and integrity manifest.

Export format 3 serializes the complete verified ledger history and a
schema-versioned live-state projection, compresses it with TGSRR's deterministic LZSS codec,
encodes it as Base64URL, and includes a SHA-256 checksum. The current live kill
total, challenge evidence (`challenge.id` and `challenge.gameMode`; each TGSRR
Last Stand file registers its own canonical ID and exact game-mode pair while
defining the challenge, and Identity resolves the live mode against those
authoritative definitions before retaining the first successful observation),
starting/current character identity, immutable pre-spawn selected trait IDs,
spawned effective trait IDs, current effective trait IDs, and a stable-ID snapshot
of every current skill's category, level, and cumulative XP are included. The
current snapshot also contains all 13 stable outpost IDs with discovery/stage
state, strict completion, weighted progress, requirement counts, observation
times, and the latest persisted value of every observed deliverable. A
rules-versioned challenge-progress snapshot records the Tracker's authoritative
kills, skills, and outposts category summaries without inventing a single
overall percentage. A sorted current loaded-mod snapshot preserves every active
Mod ID and its Workshop ID association, including local mods with no Workshop
ID. A non-mutating active-day snapshot includes the current day's start and
observation timestamps, elapsed world hours, live kill delta, and non-zero
per-skill XP deltas without prematurely sealing a historical day event.
The current projection also includes every registered town ID and its permanent
first-visit state. Visits carry their original UTC time, world age, activation
point ID, and observed coordinates; bootstrapped runs explicitly disclose a partial
town-history baseline.
Literature export schema 1 contains the immutable filtered starting baseline,
sorted current sets of full skill-book and recipe-magazine item IDs, plus sorted
per-item first/last completion times and completion counts.
Runs bootstrapped after collection begins disclose a partial baseline rather than
inventing historical read timestamps.
Non-town location export schema 1 is already present with the registry version,
partial-history flag, and registered first-visit entries. At registry version 0
the entries array is intentionally empty.
Selected traits are captured from the character-creation UI before Project
Zomboid applies spawn-time mutations. A missing capture on an already-running
or bootstrapped save uses a clearly marked partial fallback rather than claiming
that the effective spawned set was the player's original selection.
The exporter reads its generated envelope back before presenting it to the
player. Only the current development envelope format is accepted; unsupported
formats are rejected rather than migrated.

Ledger segment format 1 stores up to 256 canonical events per
`segments/events-NNNNNN.bin` file. Records are byte-length framed and hex encoded
so Build 42's append-only text writer can safely carry arbitrary canonical bytes.
A full segment receives a terminal seal containing its count, final sequence,
and final hash and is never opened again. The current segment remains appendable.
On every run load TGSRR verifies every record, segment boundary, seal, and chain
link; its final hash must match the world-scoped saved cursor, and disk may not
be missing or ahead of the save. Pre-release ledger layouts are not migrated.

Gameplay systems submit history through `TGSRR/Run/Recorder`; they do not write
files, construct sequence numbers, or manage hashes. The recorder accepts only
registered namespaced event types, supplies authoritative UTC and world-age
timestamps, updates the world-scoped chain cursor immediately after verified
write-back, rejects recursive writes, and latches integrity failures so callers
cannot silently continue an invalid chain.

The first gameplay bridge records the tracker events already treated as rising
edges: kill milestones, skill levels, completed outpost deliverables, and whole
outpost completion. Ledger payloads contain stable internal IDs and primitive
measurements only; localized labels, player objects, complete live records, and
other presentation/runtime structures are intentionally excluded.

Daily history uses one atomic `day.started` event at each `Events.EveryDays`
transition. It timestamps the new day in UTC and world age. From the second
marker onward, `completedDay` identifies the just-finished day and contains only
its non-zero scalar deltas and non-empty ID-keyed delta maps. Missing delta
fields mean zero; they do not mean unknown. `partial` and `partialMetrics` appear
only when the sealed interval began from an incomplete baseline. The first
marker has no `completedDay`; it establishes the baseline only in world-scoped
ModData and is marked partial when TGSRR was introduced to an already-running
challenge. Absolute skill/stat baselines are never repeated in ledger events.
The ledger remains the authoritative exported daily history.

Format-3 also exports the character's current authoritative Nutrition weight as
`weight.currentKilograms` with `unit = "kilogram"`. The active-day projection
contains signed `weightDeltaKilograms` from its saved day baseline, and each
`completedDay` seals the same signed delta for the preceding day. A missing
completed-day weight delta means zero. Weight is an instantaneous measurement,
so it does not carry a partial-history flag.

Nimble-stance evidence is a cumulative real-time measurement only. TGSRR adds
short consecutive wall-clock sample intervals to
`nimbleStance.movementMilliseconds` when the local player changes position on
foot while `isAiming()` is true. Standing aim, vehicles, paused play, loading
gaps, and `FishingState` are excluded; intervals over one second are discarded
rather than guessed. Bootstrapped runs mark the cumulative value partial. The
measurement has no active-day or completed-day delta.

Zombie kills credited to the local player are also classified in cumulative
`zombieKillTypes` counters: `standing`, `onfront`, `onback`, `fenceAssist`, and
`windowAssist`. Fence/window assists use a transient marker on zombie ModData
from traversal until the zombie finishes getting up; an assist overrides the
ordinary posture classification. Existing runs mark this history partial. These
counters have no daily delta.

Skill milestones are derived without adding another event type. The first
`skill.level.reached` record at exactly level 10 for each stable skill ID is
projected with its category ID, chronological completion order, event sequence,
UTC, world age, and elapsed days since run creation. Earlier levels remain in
the ledger but are not milestones. Bootstrapped runs mark milestone history
partial because already-completed level-10 transitions cannot be reconstructed.

Active run time is exported cumulatively as
`activeGameplay.milliseconds`. Following the audited Twist Stats model, TGSRR
uses a wall-clock `OnTick` accumulator and treats the visible in-game pause
menu, `isGamePaused()`, or either exposed game-speed control reporting zero as
paused. Loading, suspension, and long hitches are rejected by discarding
intervals over five seconds. Time acceleration does not multiply real time.
Bootstrapped runs mark the value partial. The value has no daily delta and does
not claim that external streaming software was broadcasting.

Completed segments are never rewritten. Periodic state snapshots contain the accepted ledger cursor/head hash and can be cross-anchored into compact global ModData. Export verifies framing, record checks, the complete hash chain, snapshot agreement, sequence continuity, and branch selection before producing a submission. Any failure is exported as an explicit integrity condition rather than silently repaired away.

This raises the effort needed to fabricate a consistent history and gives stream/VOD review useful evidence, but a determined participant who modifies the Lua implementation can still regenerate locally valid files. No encryption or HMAC key embedded in the mod is considered secret.

## Rollback, corruption, and approved recovery

Recovery creates a new declared timeline branch; it never erases or overwrites
existing history. Epoch 1 retains the original segment layout. Each later epoch
has immutable metadata at
`branches/epoch-NNNNNN.meta` and its own event segments under
`branches/epoch-NNNNNN/segments/`. The metadata binds the parent epoch, restored
checkpoint sequence/hash, superseded head sequence/hash, reason, decider,
authorization status, selected action, and a summary of superseded event types.
Its canonical payload is protected by a SHA-256 checksum.

If the external ledger head is ahead of the checkpoint embedded in a restored
save, the load is a detected rollback. Session-boundary-only tails may be
adopted automatically when the independent session cursor agrees. A tail
containing gameplay events pauses the game and presents the player with the
saved and superseded cursors plus an event-type summary. Continuing freezes the
later records as a superseded branch and starts a new epoch from the restored
checkpoint; declining leaves tracking stopped and displays the reason. Epoch
creation is idempotent, so a crash between writing immutable recovery metadata
and saving the new epoch resumes the same branch rather than inventing another.
The superseded records are not counted in the active projection.

An accepted recovery record contains at least:

- Previous ledger head and sequence.
- Restored save checkpoint hash and sequence.
- Hash of the restored normalized state.
- UTC and game-time recovery observation where available.
- Recovery reason and approval/reference ID.
- Structured decision authority as `decider.type` and `decider.id`. Automatic
  tracker recovery uses `{ type = "system", id = "tgsrr" }`; future player,
  moderator, or signed-authorization decisions retain their distinct authority.
- Previous and newly assigned epoch/branch IDs.
- Authorization status and the player's selected action.

`decider` identifies who or what selected the action; it is not an eligibility
verdict. Defined authority types are `system`, `player`, `moderator`, and
`authorization`. The `id` is a stable identifier within that type. Recovery
records created before this field was introduced remain valid and may omit it;
consumers should display their decision authority as unknown rather than infer
one from `authorizationStatus`.

For example, restoring checkpoint `C` after records `D` and `E` produces:

```text
A -> B -> C -> D -> E
          \-> Recovery -> F -> G
```

`D` and `E` remain in the export as superseded history. Accepted totals follow `A -> B -> C -> Recovery -> F -> G`, preventing the restored period from being double counted.

If a ledger segment is damaged, scan only to the last structurally and cryptographically valid record. Preserve or quarantine the damaged bytes and record their hash. A new recovery segment may begin from the last valid head only through the same declared recovery process. Length-prefixed records and immutable segments should allow an incomplete final write caused by sudden power loss to be distinguished from damage to previously committed history.

Organizer approval may be delivered without live in-game networking through a signed recovery-authorization file. The website signs the run ID, previous ledger head, restored checkpoint, reason, approval ID, and permitted action with its private key. TGSRR contains only the public verification key and embeds the signed authorization into the recovery record/export. Exact signature algorithm and import flow remain implementation decisions.

Exports distinguish at least:

- Normal uninterrupted continuation.
- Detected unauthorized rollback or corruption.
- Organizer-authorized recovery with superseded history retained.
- Player choice to continue after the detected condition.

Format-3 places recovery evidence in `projection.recovery`:

- `present`, `hasBranches`, and neutral `status` (`uninterrupted` or
  `recovery_present`);
- `activeEpoch`;
- `decisions`, derived from active-chain `run.recovery.decided` records;
- `recoveries`, containing each immutable metadata record and
  `supersededBodies`, the complete canonical event bodies after its checkpoint.

This is evidence, not a verdict. The first website submission containing a new
recovery can be flagged for moderator approval or denial. Once the website
accepts that report as its new comparison baseline, later exports continue from
the same active epoch and need no further recovery review unless another
recovery appears.

## Power-cut clock reconciliation

Project Zomboid persists the visible calendar separately from its world-age
clock. `worldAgeHours` is derived from `nightsSurvived` and `timeOfDay`, while
the character's `hoursSurvived` counter is stored independently. A power-cut
failure can therefore reset year/month/day without resetting character survival
time, and may or may not also reset world age.

TGSRR writes two alternating local files,
`TGSRR/Runs/<runId>/clock-a.checkpoint` and `clock-b.checkpoint`, only from
`OnPostSave`. Each canonical, SHA-256-checksummed slot contains a monotonically
increasing slot sequence, the saved event sequence/hash, UTC, calendar,
time of day, nights survived, world age, and character hours survived. Writing
the older slot preserves the preceding valid checkpoint if power fails during
the new write. The slot is read back and verified immediately. These raw local
recovery files are not included in the submission export.

Reconciliation is eligible only when the loaded run cursor exactly matches the
checkpoint cursor, character hours have not regressed, and the current load is
not entering a declared gameplay-rollback recovery. A recovered save's older
calendar and world age belong to its selected branch and are never advanced to
the abandoned branch's clock. The next successful save writes a fresh
checkpoint anchored to the recovered branch, after which future genuine clock
corruption can be detected normally. For eligible loads, expected world age is
the anchored world age plus the increase in character hours; expected calendar
and time of day are advanced by the same delta. A two-in-game-minute tolerance
absorbs adjacent-frame floating-point sampling. Exact agreement is a read-only
no-op and normal initialization continues unchanged.

Any independently proven disagreement pauses before the new `session.started`
event. The player may apply the reconstructed year, month, day, time of day,
and nights-survived values, with immediate readback verification, or decline
and leave tracking stopped with gameplay paused for a deliberate save/quit
decision. A successful repair appends `run.clock.repaired`
with observed/restored clocks, checkpoint cursor/checksum, reason, and player
decision authority. The complete event is exported for moderator review. A
checkpoint cursor mismatch is never used to alter the clock; character-hours
regression is ambiguous and stops tracking rather than guessing.

## Loaded-mod session history

At run creation, write sorted full sets of active mod IDs and unique Workshop
IDs, plus their mapping. At every later game load, compare the newly sorted
mapping against the last committed mapping and append a timestamped session
record containing:

- Session sequence.
- Time record.
- Added and removed mod IDs.
- Added and removed Workshop IDs.
- Changed Mod ID associations, including the previous and current Workshop ID.
- Optional current-set hash.
- Game version and TGSRR version.

Every load retains a timestamped session-start record, but unchanged sessions
do not repeat the complete identifier sets. The latest complete mapping is kept
in world-scoped run state.

Global ModData should retain only the run ID, latest session sequence, latest mod set or hash, and file cursor needed to recover an interrupted append. The full session history belongs in the file stream.

## Export boundary

The exporter consumes normalized TGSRR records, never Tracker UI rows or localized presentation strings. Each exported capability uses the applicable TGSRR schema version.

Website database mappings are presentation/integration metadata. A missing website mapping must not make an otherwise valid in-game ID disappear from an export.

## Open decisions

- Final segment rollover threshold and whether the append-safe on-disk
  representation should change after Build 42.
- Snapshot cadence, flush policy, and which compact integrity anchors are duplicated into global ModData.
- Offline recovery-authorization signature algorithm and import/user-interface flow.
- Definition and granularity of a location visit.
- Whether unchanged mod sets produce a session record or only a session-start timestamp referencing the prior set.
