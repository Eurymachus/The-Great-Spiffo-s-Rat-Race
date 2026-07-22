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
- Towns: stable TGSRR/integration town ID.
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
- Weapon kills and broken weapons: TGSRR attribution and aggregate counters keyed by full item type.
- Day starts, visits, literature, milestones, outposts, distance, injuries, animals, production, and mod sessions: TGSRR records using their appropriate events, aggregates, or semantic checkpoints.

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
- `milestones`: export projection of the existing milestone ledger where required.

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
initializes. This codec is the
canonical content layer for the binary ledger; the existing `sessions.log`
remains the temporary session diagnostic until ledger migration is complete.

IDs may be interned and numeric values delta encoded. Optional compression is permitted after canonical encoding. Base64 or XOR alone are not integrity measures and must not be presented as security.

Suggested run artifacts:

- `run.meta`: versioned run identity and format metadata.
- `events-NNNN.bin`: immutable completed event segments and one appendable current segment.
- `state-current.bin`: atomically replaced canonical current-state snapshot.
- `recovery-NNNN.bin`: immutable recovery evidence/authorization segments where needed.
- `run.export`: generated submission envelope containing the data and integrity manifest.

Completed segments are never rewritten. Periodic state snapshots contain the accepted ledger cursor/head hash and can be cross-anchored into compact global ModData. Export verifies framing, record checks, the complete hash chain, snapshot agreement, sequence continuity, and branch selection before producing a submission. Any failure is exported as an explicit integrity condition rather than silently repaired away.

This raises the effort needed to fabricate a consistent history and gives stream/VOD review useful evidence, but a determined participant who modifies the Lua implementation can still regenerate locally valid files. No encryption or HMAC key embedded in the mod is considered secret.

## Rollback, corruption, and approved recovery

Recovery creates a new declared timeline branch; it never erases or overwrites existing history.

If the external ledger head is ahead of the checkpoint embedded in a restored save, the load is a detected rollback. For an official run, normal play must pause until the recovery is either authorized, the player quits, or the run permanently continues as unofficial. The existing later records remain preserved as a superseded branch and are not counted again in accepted aggregates.

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
- Player choice to continue unofficially.

## Loaded-mod session history

At run creation, write sorted full sets of active mod IDs and unique Workshop IDs, plus their mapping. At every later game load, compare the newly sorted sets against the last committed sets and append a timestamped session record containing:

- Session sequence.
- Time record.
- Added and removed mod IDs.
- Added and removed Workshop IDs.
- Complete mod ID to Workshop ID mapping for the session, preserving entries with no Workshop ID.
- Optional current-set hash.
- Game version and TGSRR version.

An unchanged session may still need a timestamped session-start record because the requirement is to show which mod set was active for each session. The record may omit repeated IDs and refer to the previous set through its sequence/hash.

Global ModData should retain only the run ID, latest session sequence, latest mod set or hash, and file cursor needed to recover an interrupted append. The full session history belongs in the file stream.

## Export boundary

The exporter consumes normalized TGSRR records, never Tracker UI rows or localized presentation strings. Each exported capability uses the applicable TGSRR schema version.

Website database mappings are presentation/integration metadata. A missing website mapping must not make an otherwise valid in-game ID disappear from an export.

## Open decisions

- Exact binary field layout, segment rollover thresholds, compression, and corruption-check algorithm.
- Snapshot cadence, flush policy, and which compact integrity anchors are duplicated into global ModData.
- Offline recovery-authorization signature algorithm and import/user-interface flow.
- Definition and granularity of a location visit.
- Canonical town registry and boundary source.
- Authoritative event path for completed literature.
- Whether unchanged mod sets produce a session record or only a session-start timestamp referencing the prior set.
