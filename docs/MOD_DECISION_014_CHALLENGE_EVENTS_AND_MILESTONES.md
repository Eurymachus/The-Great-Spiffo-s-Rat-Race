# Decision 014: Challenge events and milestones

## Decision

Challenge systems publish domain events through a shared event bus. A registry matches those events to milestone definitions, applies mode/option gates, records one-time claims in a persistent ledger, performs an optional award, and then emits `milestone.awarded` for presentation.

## Initial events

- `outpost.deliverable.changed`
- `outpost.deliverable.completed`
- `outpost.completed`
- `kills.milestone.reached`
- `milestone.awarded`

Deliverable and outpost completion events are rising-edge events. Establishing the first authoritative observation does not create a retroactive completion award.

## Scope and persistence

- Dynamic claim keys allow a single definition to award once per outpost deliverable, once per outpost, or once per character threshold.
- The milestone ledger is independent from tracker presentation and stores only serializable claim metadata.
- Award definitions may declare challenge modes or an `enabled` callback, leaving room for future challenge options without coupling producers to policy.

## Kill milestones

The initial ladder is 1,000; 10,000; 25,000; 50,000; 100,000; 250,000; 500,000; 750,000; and 1,000,000 kills. Thresholds are checked only when the authoritative character kill count refreshes from `OnZombieDead`. The first observed total establishes a baseline and does not replay older notifications.

## Future skills integration

Skills should publish a domain event such as `skill.level.reached` containing the skill identifier and level. Per-skill/per-level definitions can then use the same registry, ledger, gating, award, and notification path.
