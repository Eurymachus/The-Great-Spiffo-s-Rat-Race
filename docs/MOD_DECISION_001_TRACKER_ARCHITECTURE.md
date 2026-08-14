# MOD Decision 001: Tracker Architecture

- Status: Accepted
- Date: 2026-07-16

## Context

The Rat Race will track several finite challenge systems. A single outpost-specific window would not scale to additional deliverables, while placing every detail on one page would create a dense and disjointed UI.

## Decision

Use a modular tabbed tracker:

- A generic registry supplies ordered modules.
- A fixed-size window owns tabs, visibility, position, and persistence.
- Overview presents aggregate challenge deliverables.
- Dedicated tabs present system-specific detail.
- Inspectors provide the deepest explanation for individual records.

Use a contiguous tab strip and spacing language consistent with Daily Report Journal.

## Consequences

- New systems can register without modifying the tracker shell.
- Overview requires a common deliverable data contract.
- Detailed modules may use specialized layouts.
- Fixed dimensions simplify layout, but the final size must be chosen after Overview requirements are known.
- Provisional system checks must not become implicit permanent UI contracts.

## Related documents

- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_DECISION_002_OVERVIEW_DELIVERABLES.md](MOD_DECISION_002_OVERVIEW_DELIVERABLES.md)
- [MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md](MOD_DECISION_008_PLAYER_AND_DEBUG_UI.md)
