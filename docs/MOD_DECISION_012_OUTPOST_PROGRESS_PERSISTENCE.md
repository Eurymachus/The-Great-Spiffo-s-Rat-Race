# Decision 012: Outpost Progress Persistence

## Context

Exports must include the last known state of every discovered outpost, including outposts not loaded or visited during the current play session. Re-running live checks every second must not produce unnecessary persistent writes.

## Decision

- World-level `ModData` under `TGSRR_OutpostProgress` stores one record per outpost.
- Each deliverable uses the common persisted contract: `available`, `passed`, `current`, `required`, optional presentation `state`, and `observedAt`.
- Live world checks remain authoritative while an outpost is loaded and the player is in its clearance area.
- The most recent authoritative result remains the exportable last-known snapshot after the area unloads.
- A runtime last-written cache compares only meaningful deliverable fields. `ModData` changes only when one of those fields changes.
- `observedAt` is assigned on a meaningful state change and is excluded from equality comparisons.
- Optional `state` distinguishes meaningful presentations that cannot be inferred from numeric progress, such as `none`, `not_connected`, and `fuel` for a generator, or `none`, `not_plumbed`, `source_missing`, and `connected` for a sink.
- Debug details, Java object references, localized strings, scan counts, and transient errors are not persisted.
- Expected exterior-envelope geometry is cached at runtime; physical openings are reclassified from that geometry so topology changes update persisted aggregates.
- Development schemas are disposable until release compatibility is explicitly adopted; no migration is required yet.

## Consequences

- Tracker and export consumers can read all known outposts without forcing remote world scans.
- Unavailable or partially loaded checks do not erase a previous authoritative snapshot.
- The live scanner can run frequently while persistent writes remain rare.
- The current schema may reset development-save outpost progress when it changes.
