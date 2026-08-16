# Ideas Parking Lot

These are possibilities, not approved current scope. Promote an idea into
the relevant `WEBSITE_NOW.md` or `MOD_NOW.md` only when the user explicitly makes
it part of the active deliverable.

## Participant Platform

- Rework the desktop navigation bar and responsive hamburger navigation as one
  coherent interaction system. Revisit spacing, alignment, hierarchy,
  open/close behaviour and third-level navigation on both layouts rather than
  continuing with isolated cosmetic adjustments.
- Add a signed-in, filterable Run History page.
- Add a concise public Top Ten summary if it provides a useful destination
  beyond the configurable Rankings page.
- Add signed-in participant search as a discovery layer for public profiles.
- Add separately cached provider online status to ranking rows.
- Expand approved run details with useful chronology, comparisons, and charts.
- Aggregate charts such as traits and weapons used

## Challenge Operations

- Seasons and versioned rules
- Appeals and public integrity policies
- Achievements and shareable result cards
- Discord role synchronisation and challenge announcements. Participants first
  link their immutable Discord identity through the website's minimal
  `identify` OAuth flow. A later phase may use the existing **The Great
  Spiffo** bot from the same Discord application, currently hosted through
  MEE6 Custom Bot, for narrowly scoped and audited role changes. MEE6 may
  continue hosting ordinary bot features while the website uses Discord's REST
  API for role updates. Any bot-token reset must be coordinated between MEE6
  and the website. Define explicit Rat Race status-to-role mappings, preserve
  role hierarchy constraints, and avoid enabling broader permissions or
  gateway intents solely for website synchronisation.

## Report Data

- Per-day aggregate deltas
- Public presentation of lifetime kills by weapon, literature, and collectible
  evidence already present in approved exports.
- Revisit the fixed-size outpost lifecycle envelopes. Consider reducing
  `firstCompletion`, `latestCompletion`, and `latestRegression` to only
  `gameDay` and `utc` when the omitted state, sequence, requirement, and world
  age values are already authoritative elsewhere or can be derived without
  weakening validation or immutable evidence.
- Additional versioned report-schema and synthetic long-run size tests when the
  export contract changes.
