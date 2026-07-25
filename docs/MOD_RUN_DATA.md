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
- Books and magazines read and read times.
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
- Literature completion: run initialization enumerates PZ's actual persisted
  completed-page, `AlreadyReadBook`, literature-title, and print-media state
  into one immutable `literature.baseline`. It does not infer reading from known
  recipes or skill level. TGSRR wraps the successful local-player
  `ISReadABook.complete()` edge and appends one `literature.read` delta carrying
  the full item ID, stable classification, learned recipe IDs, literature-title
  IDs, print-media IDs, UTC, and world age. Repeat leisure reading remains a
  legitimate completion; reopening already-completed paged literature does not.
- Non-town locations: the collector and export contract are registry-driven,
  but the canonical definition list is deliberately deferred. Registry version
  0 contains no locations and exports an authoritative empty list. When the
  first definition set is approved, incrementing the registry version makes the
  existing one-second position check record permanent `location.visited` events
  with stable location/point IDs, UTC, world age, and observed coordinates.
  Runs that predate a populated registry are then marked partial automatically.
- Broken weapons use Build 42 `OnBreak` callbacks where defined and a short
  post-`OnWeaponSwing` condition check otherwise. The same item is weakly
  deduplicated across both paths. TGSRR appends one `weapon.broken` event with
  the original full item ID, maintains cumulative per-ID totals, and seals daily
  deltas.
- Distance travelled uses `Events.OnPlayerMove` and planar player-coordinate
  deltas, matching the established Twist Stats interpretation of one world unit
  as one metre and including vehicle movement. TGSRR adds a real-time
  speed/step bound to reject teleports and loading discontinuities, retains only
  cumulative metres and a rejected-sample count, and seals daily metre deltas.
- Day starts, visits, literature, milestones, outposts, injuries, animals,
  production, and mod sessions: TGSRR records using their appropriate events,
  aggregates, or semantic checkpoints.

High-frequency values are not appended on every tick. TGSRR records meaningful state transitions and periodic/session/day checkpoints so the canonical history remains compact.

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

The canonical event codec is now implemented as schema 1. Values are explicitly
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
total, raw challenge evidence (`challenge.id` and `challenge.gameMode`; the
first observed challenge ID is retained because PZ clears its live ID while
loading an existing save),
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
point ID, and observed coordinates; migrated runs explicitly disclose a partial
town-history baseline.
Literature export schema 1 contains the immutable starting baseline, sorted
current sets of full literature item IDs, literature-title IDs, and print-media
IDs, plus sorted per-item first/last completion times and completion counts.
Runs migrated after collection begins disclose a partial baseline rather than
inventing historical read timestamps.
Non-town location export schema 1 is already present with the registry version,
partial-history flag, and registered first-visit entries. At registry version 0
the entries array is intentionally empty.
Selected traits are captured from the character-creation UI before Project
Zomboid applies spawn-time mutations. A missing capture on an already-running
or migrated save uses a clearly marked partial fallback rather than claiming
that the effective spawned set was the player's original selection.
The exporter reads its generated envelope back before presenting it to the
player. Format 1 and 2 envelopes remain decodable for pre-release test runs.

Ledger segment format 1 stores up to 256 canonical events per
`segments/events-NNNNNN.bin` file. Records are byte-length framed and hex encoded
so Build 42's append-only text writer can safely carry arbitrary canonical bytes.
A full segment receives a terminal seal containing its count, final sequence,
and final hash and is never opened again. The current segment remains appendable.
On every run load TGSRR verifies every record, segment boundary, seal, and chain
link; its final hash must match the world-scoped saved cursor, and disk may not
be missing or ahead of the save. The earlier one-record binary prototype is
verified and packed automatically for pre-release test runs without changing
event hashes.

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
transition. It timestamps the new day in UTC and world age while carrying the
just-completed day's kill delta and non-zero XP deltas keyed by the same internal
perk IDs used by the Skills tracker. The first event establishes absolute kill
and per-skill XP baselines and is marked partial when TGSRR was introduced to an
already-running challenge. Baselines live in world-scoped run state; the ledger
remains the authoritative exported history.

Completed segments are never rewritten. Periodic state snapshots contain the accepted ledger cursor/head hash and can be cross-anchored into compact global ModData. Export verifies framing, record checks, the complete hash chain, snapshot agreement, sequence continuity, and branch selection before producing a submission. Any failure is exported as an explicit integrity condition rather than silently repaired away.

This raises the effort needed to fabricate a consistent history and gives stream/VOD review useful evidence, but a determined participant who modifies the Lua implementation can still regenerate locally valid files. No encryption or HMAC key embedded in the mod is considered secret.

## Rollback, corruption, and approved recovery

Recovery creates a new declared timeline branch; it never erases or overwrites existing history.

If the external ledger head is ahead of the checkpoint embedded in a restored save, the load is a detected rollback. Normal play may need to pause until a recovery decision is recorded. The existing later records remain preserved as a superseded branch and are not counted again in accepted aggregates. The mod exports the rollback and recovery evidence; the website and moderator determine any eligibility consequence.

An accepted recovery record contains at least:

- Previous ledger head and sequence.
- Restored save checkpoint hash and sequence.
- Hash of the restored normalized state.
- UTC and game-time recovery observation where available.
- Recovery reason and approval/reference ID.
- Previous and newly assigned epoch/branch IDs.
- Authorization status and the player's selected action.

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
in world-scoped run state and reconstructed from legacy full session records
when migrating a pre-release test run.

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
