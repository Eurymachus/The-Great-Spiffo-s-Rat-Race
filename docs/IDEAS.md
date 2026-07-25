# Ideas Parking Lot

These are possibilities, not approved current scope. Promote an idea into
the relevant `WEBSITE_NOW.md` or `MOD_NOW.md` only when the user explicitly makes
it part of the active deliverable.

## Participant Platform

- Participant accounts and profiles
- Paste-to-submit encoded run updates
- Moderator approval, rejection, review, and invalidation tools
- Public leaderboards with active and ended runs
- Detailed player and run analysis
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

- Original and current traits
- Current skill levels
- Per-day aggregate deltas
- Lifetime kills by weapon
- Outpost progress
- Versioned report schema and synthetic long-run size tests
