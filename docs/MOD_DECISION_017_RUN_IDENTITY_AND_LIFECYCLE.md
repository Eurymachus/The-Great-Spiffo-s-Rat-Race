# Decision 017: Run Identity and Lifecycle

## Decision

Every Rat Race world owns one immutable TGSRR run ID. The run ID is distinct from the character name and is the only canonical run identity.

The run ID is minted once, stored in world-scoped global ModData, and used as the run-file directory key. The starting ironman character is permanently associated with that run. Its starting forename, surname, and display name are exported as presentation metadata.

Existing saves first opened after this feature is introduced are supported. Their run is marked as bootstrapped, with the current state becoming the initial observed baseline; the implementation does not claim that the external ledger predates that bootstrap.

## Identity sources

- Canonical run identity: TGSRR global ModData.
- File root: `TGSRR/Runs/<runId>/` under the Zomboid Lua storage area.
- Starting character name: captured from the associated character descriptor.
- Challenge evidence: the exact current Project Zomboid challenge ID and game
  mode, captured at run creation and every session boundary.

Character names are mutable and non-unique. A name change never changes the run ID.

## Lifecycle

The factual mod-side lifecycle begins with `active`. Later observed transitions
may record events such as character death, completion, abandonment, or a recovery
condition. These observations are distinct from website-owned submission status
and run eligibility.

The mod does not store or export an authoritative `official`, `unofficial`, or
`unclassified` verdict. It exports neutral evidence. The website applies the
current competition rules and a moderator can approve or decline a submission
and determine run eligibility.

Continuing after a recovery decision does not create a new run ID. An approved
recovery creates a new epoch/branch inside the same run, as specified in
`MOD_RUN_DATA.md`; its eligibility effect is decided outside the mod.

## Session boundary

Each game load appends one session-start record containing:

- Run ID and session sequence.
- UTC time and world age.
- Exact current challenge ID and game mode. Unknown or changed values are retained
  as evidence rather than rejected or normalized.
- Current character name.
- Sorted complete active-mod ID set and unique Workshop-ID set.
- Mod ID to Workshop ID mapping, including local/unpublished entries with no Workshop ID.
- Added and removed deltas for both identifier sets compared with the preceding session.

The latest session cursor and mod set are retained compactly in global ModData. Growing session history belongs in the run files.

## Initial implementation boundary

The first implementation creates and validates identity metadata and session history. It detects missing or mismatched run metadata and reports an integrity condition, but does not yet present the recovery decision UI or select recovery branches.
