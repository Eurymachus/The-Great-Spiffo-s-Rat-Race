# Mod: Challenge Contract

## Original purpose and experience

The Great Spiffo's Rat Race is an extreme, long-form Project Zomboid ironman challenge. It combines total character mastery, one million zombie kills, and restoration of 13 church outposts into a single streamed run. The tracker should clarify progress without weakening or changing the challenge.

## Accepted official rules

- Avoid exploits; some are difficult to avoid, but the goal is to avoid as many as possible.
- Use the listed settings and approved mods.
- Stream the entire run for bounty eligibility. Offline runs may participate but are not bounty-eligible.
- Debug may be used only for lethal bugs that can be proven not to be player error.
- One character and one world per attempt. Participants may start new attempts as often as needed.
- Any combination of character traits and occupations is allowed.

## Accepted win condition

- Reach level 10 in every registered child skill discovered from `PerkFactory.PerkList`, including mod-added skills.
- Clear and complete every listed outpost and its requirements.
- Record 1,000,000 total zombie kills in the character information tab.

## Current implementation

- Standard, CDDA, and Sprinters challenge variants exist, identified by the raw
  Project Zomboid IDs `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters`.
- Character respawn is removed for all three variants.
- Sandbox configuration is supplied by the challenge scripts/configuration.
- The tracker reads the Character Info zombie-kill counter and exposes normalized outpost progress.
- The Skills tracker dynamically discovers every perk whose parent is not `Perks.None` and verifies mastery from that perk's live level reaching 10.

## Historical intent

- Twitch tag `RATRACE` was used so organizers could find streamed runs.
- Discord was the support and rules-discussion venue.
- The official challenge was associated with leaderboard/bounty submission; unofficial variants were for fun and not leaderboard-eligible.

These communication and submission details are product history, not eligibility
verdicts emitted by the mod. The website maps challenge IDs for presentation and
applies current competition policy to exported evidence.

## Open questions

- Should variants display different historical or submission/bounty messaging?
- Where should the approved mod list, settings file, and current organizer links be presented?

## Related documents

- [MOD_NOW.md](MOD_NOW.md)
- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_003_CHALLENGE_CONTRACT.md](MOD_DECISION_003_CHALLENGE_CONTRACT.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
- [MOD_DECISION_016_SKILL_TRACKING.md](MOD_DECISION_016_SKILL_TRACKING.md)
