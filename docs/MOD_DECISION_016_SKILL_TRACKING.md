# Decision 016: Skill Tracking

## Decision

The Rat Race requires the single ironman character to reach level 10 in every registered skill.

The accepted skill set is discovered from `PerkFactory.PerkList` using the same child-perk rule as vanilla Character Info: every perk whose parent is not `Perks.None` is tracked. This includes registered mod skills without requiring a hard-coded TGSRR list.

## Presentation

- Skills are grouped under their localized vanilla parent categories.
- Category rows can be collapsed and show mastered-skill counts plus aggregate fractional category progress.
- Collapsed category choices persist across sessions in the tracker INI state.
- Collapse toggles update cached state only; dirty INI state is written by the vanilla `OnSave` lifecycle rather than from presentation input.
- Each skill row shows its localized name, current level out of 10, and ten discrete progress segments.
- Completed levels fill whole segments; XP toward the next level partially fills the current segment.
- Skill names and level pips follow vanilla boost and acquired/current/locked colouring, while aggregate category/footer bars retain tracker green.
- The Skills table permanently reserves its scrollbar gutter so collapsing categories never changes column or pip geometry.
- The fixed footer shows mastered skills / total skills and aggregate fractional progress.
- Aggregate progress is the sum of fractional skill levels divided by `skill count * 10`.

## Runtime and milestones

- `Events.AddXP` invalidates the cached presentation snapshot.
- `Events.LevelPerk` invalidates the snapshot and emits `skill.level.reached` with skill, category, and level fields.
- Award policy is deliberately unresolved. Consumers may later register awards for individual skill levels, skill mastery, category milestones, or another mode-specific rule without changing the producer event.
