# Decision 017: Run Identity and Lifecycle

## Decision

Every Rat Race world owns one immutable TGSRR run ID. The run ID is distinct from the character name and is the only canonical run identity.

The run ID is minted once, stored in world-scoped global ModData, and used as the run-file directory key. The starting ironman character is permanently associated with that run. Its starting forename, surname, and display name are exported as presentation metadata.

Existing saves first opened after this feature is introduced are supported. Their run is marked as bootstrapped, with the current state becoming the initial observed baseline; the implementation does not claim that the external ledger predates that bootstrap.

## Identity sources

- Canonical run identity: TGSRR global ModData.
- File root: `TGSRR/Runs/<runId>/` under the Zomboid Lua storage area.
- Starting character name: captured from the associated character descriptor.
- Challenge variant: captured from the active Project Zomboid challenge ID and game mode.

Character names are mutable and non-unique. A name change never changes the run ID.

## Lifecycle

The normalized lifecycle begins with `active`. Later transitions may produce `completed`, `abandoned`, `recovery_required`, or `invalid`. Official classification is a separate field so lifecycle and verification policy do not become conflated.

Until challenge-mode registration explicitly assigns verification policy, the foundation records `unclassified`. It must not silently label a bootstrapped development save as an official run.

Continuing after a disqualifying decision may permanently change official classification to `unofficial`; it does not create a new run ID. Approved recovery creates a new epoch/branch inside the same run, as specified in `MOD_RUN_DATA.md`.

## Session boundary

Each game load appends one session-start record containing:

- Run ID and session sequence.
- UTC time and world age.
- Challenge ID and game mode.
- Current character name.
- Sorted complete active-mod ID set and unique Workshop-ID set.
- Mod ID to Workshop ID mapping, including local/unpublished entries with no Workshop ID.
- Added and removed deltas for both identifier sets compared with the preceding session.

The latest session cursor and mod set are retained compactly in global ModData. Growing session history belongs in the run files.

## Initial implementation boundary

The first implementation creates and validates identity metadata and session history. It detects missing or mismatched run metadata and reports an integrity condition, but does not yet present the recovery decision UI or select recovery branches.
