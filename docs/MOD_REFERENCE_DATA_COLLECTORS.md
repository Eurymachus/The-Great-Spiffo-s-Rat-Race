# Reference Collector Research

## Purpose

This document records useful collection techniques found in unrelated mods and their supporting applications. They are research references only.

TGSRR has no runtime integration with these mods. It does not read their identities or data, write their formats, select them as authorities, or change behaviour based on whether they are installed. The Tracker presents the canonical data collected by TGSRR itself.

Reference source is read-only unless a separate change is explicitly requested.

## Daily Report Journal

Audited source:

- Local workspace: `C:\Users\refle\Zomboid\Workshop\Daily Report Journal`
- Version: `42.19`
- Main store: `client/DRJ/DRJ_FileStore.lua`
- XP store: `client/DRJ/DRJ_XPLog.lua`
- RAM projection: `client/DRJ/DRJ_RAM.lua`
- Mod ID: `dailystatisticsandgains`

### Observed identity and files

DRJ's stable single-player identity is the player ModData key `EURY_DRJ_PersistentUniqueID`. Its one-time migration preserves the value from historical keys. This is documented solely to understand DRJ; TGSRR does not read or export it.

DRJ creates a character-scoped root at `DailyReportJournal/<charKey>/` under the Zomboid Lua storage area. `journal.djr` begins with:

```text
DRJ|char=<charKey>|created=<unix-seconds>
```

Daily records are append-only `J` lines. Their current normalized fields include survivor day, world day, real timestamp, in-game date, per-perk XP deltas keyed by internal perk ID, daily zombie-kill delta, average kills, weight, weight delta, total skill XP, and score.

The public file-store API includes initialization, `appendDaily`, `readTail`, `readAll`, character-root path helpers, and character-root readers/writers. `DRJ_RAM` hydrates from disk and keeps UI reads off the file hot path.

### XP events

`DRJ_XPLOG` records `Events.AddXP` entries by internal perk ID with survivor day, hour, minute, and amount. It exposes `subscribe`, `get`, `listPerks`, `load`, and `save`.

The event log is intentionally capped at the latest 50 entries per perk. It is useful for recent presentation, not a complete long-run export. Complete daily per-skill history belongs to `journal.djr`.

Dirty XP state flushes on `Events.OnSave`.

### Lessons for TGSRR

- A daily record timestamp and an explicit day-began timestamp are different facts; TGSRR records the latter explicitly.
- File-backed history, a hydrated RAM projection, and dirty-on-save flushing are useful implementation patterns.
- TGSRR implements these patterns in its own schema and storage.

## Better Creator Tools

Audited source:

- Local workspace: `C:\Users\refle\Zomboid\Workshop\Better Creator Tools`
- Latest local version: `42.15`
- Trait store: `client/EURY_TRAITLOGGER/TraitLogger.lua`
- Persistent identity: `shared/EURY_TRAITLOGGER/PersistentID.lua`
- Skill snapshot export: `client/EURY_TRAITLOGGER/SkillsExport.lua`
- Mod ID: `EURY_TRAITLOGGER`

### Identity and files

The logger stores a persistent character ID in player ModData under `EURY_TRAITLOGGER_PersistentUniqueID`. Single-player authority mints the ID from character name plus a real timestamp. Files live under `playertraits/`, with a character-specific raw snapshot and localized output files.

The starting snapshot preserves profession and trait IDs. Build 42.13+ trait IDs are namespaced values such as `base:Strong`; legacy builds may expose unnamespaced IDs.

The logger captures the character-creation selection where possible and otherwise creates the initial snapshot from the first available player object. It never overwrites an existing character snapshot.

### Current traits and differential output

Current traits are collected from `CharacterTraits:getKnownTraits()` on current Build 42, falling back to legacy `getTraits()`. Better Creator Tools also creates a human-readable `traits_differential.txt`; TGSRR does not consume it.

Initialization occurs on `Events.OnCreatePlayer`; differential output is refreshed on `Events.EveryDays`.

### Lessons for TGSRR

- TGSRR captures its own starting trait snapshot and exports raw IDs, never localized labels.
- The current-trait set can be queried directly from the live player using the same Build 42 path.
- TGSRR exports starting and current ID sets. The website derives added and removed traits by comparing those sets.
- No trait differential file, timestamped trait-change history, or ID-preserving differential API is required for the current export contract.

## TwisTonFire Stats

Audited source:

- Workshop item: `3480305133`
- Mod ID: `twistonfirestats`
- Version: `42.19` single-player variant
- Weapon collector: `client/TTF_KillStats.lua`
- General statistics: `client/TwisTonFireStats.lua`

The single-player implementation stores its identity in player ModData as `PersistentUniqueID`. TGSRR does not read or export this unrelated field.

The multiplayer variants were not selected as Rat Race authorities because the current challenge is single-player ironman.

### Observed weapon-kill model

Weapon kill statistics are stored in player ModData at `TTF_KillStats`:

```lua
{
    categories = { [categoryId] = count },
    weapons = { [fullItemType] = count },
    brokenWeapons = { [fullItemType] = count },
    brokenWeaponsTotal = number,
    vehicleKills = number,
}
```

Weapon IDs use `InventoryItem:getFullType()`. Special kill sources use `__VEHICLE__` and `__UNARMED__`. The collector attributes kills through weapon-hit, swing, zombie-death, vehicle-driver, and short-lived last-hit tracking. `TTF_KillStats.Get(playerNum)` is the public read API.

### Other state

The general Stats mod uses player ModData for daily-kill baselines, distance, persistent identity, and other compact live counters. It also writes user-facing files such as daily kill records, trait presentation, settings, and window position.

### Lessons for TGSRR

- TGSRR maintains its own weapon and weapon-class aggregates using equivalent authoritative game flows where appropriate.
- Website export uses full item IDs and TGSRR-owned pseudo IDs for non-item sources.
- TGSRR does not read or write `TTF_KillStats`.
- TGSRR's implemented collector credits only deaths whose `getAttackedBy()` is
  the active Rat Race player. It preserves the weapon captured by
  `OnWeaponHitCharacter`, then resolves vehicle, unarmed, and unknown sources
  explicitly at `OnZombieDead`. Delayed fire deaths are excluded, matching
  vanilla's decision to clear `attackedBy` and not increment player kills. It
  does not copy the reference mod's data schema or treat that mod as runtime
  authority.

## Additional TGSRR capabilities

The audited versions do not provide authoritative histories for:

- Locations visited and visit times.
- Towns visited and visit times.
- Loaded-mod session history.

These require TGSRR collectors and stable in-game or TGSRR IDs rather than localized names.

TGSRR now supplies its own literature history by baselining PZ's persisted read
collections and wrapping the vanilla `ISReadABook.complete()` transition. It
does not read another mod's state or infer a publication from recipe knowledge.

Generator knowledge is independently observed through
`IsoGameCharacter:isRecipeActuallyKnown("Generator")`. This avoids treating
`Base.ElectronicsMag4` as the only route: Build 42 also grants the recipe to the
Electrician profession and at Electrical level 3, reduced to level 2 by
Inventive. TGSRR records one first-observed milestone with contemporaneous
evidence and does not assert which route caused it.

PZ does not expose a general wound-created Lua event. `OnPlayerGetDamage`
reports repeated health loss from causes such as bleeding, fire, hunger,
poison, vehicles, and weapons, and is not emitted by the zombie
scratch/laceration/bite mutation path. TGSRR therefore reconciles the fixed set
of `BodyPart` injury flags on `OnPlayerUpdate`. This captures distinct
false-to-true injury manifestations without wrapping the many unrelated Java
and Lua creation paths. Zombie association additionally requires a
contemporaneous zombie `attackedBy` object with `AttackDidDamage`; the exported
name remains deliberately non-causal because PZ stores neither wound IDs nor
durable wound-source attribution.

## Storage conclusion

Global ModData and player ModData are serialized save state, not unbounded databases. There is no useful project-level promise that they may be made arbitrarily large. Large nested histories increase save size, serialization cost, load cost, and multiplayer synchronization risk; large player ModData has also proven fragile in practice.

Use ModData for compact authority only:

- Run ID and schema version.
- Last committed sequence/cursor per stream.
- Last known loaded-mod set/hash for delta recovery.
- Small aggregates required by gameplay.

Use character/run-scoped files for append-only or growing histories, with RAM projections for runtime queries and change-only or save-lifecycle writes.

## PZCommunityRank Companion and backend (19 November 2026)

### Conclusion and correction

The Brazilian challenge combines automated mod telemetry, Companion uploads,
backend sanity checks and moderator-certified objectives. The earlier Lua-only
comparison was incomplete: absence of an in-game equipment or clearance check
does not mean the overall challenge accepts that objective without review.
The backend has an explicit moderator approval path, and its documentation
records an example of base points being checked against a VOD.

This is reference research, not approval to adopt their requirements or add a
TGSRR Companion application.

### Sources and limits

- Installed Workshop `3746228308`, `PZCommunityRank` Lua version `2.36.0`.
- [Official downloads](https://www.pzrank.com.br/links) advertised Companion
  `v2.7.0`, with an [official release](https://github.com/lbcamargo94/PZ-Rank-Companion-Releases/releases/tag/v2.7.0).
- The release repository describes the source as private, but Companion source
  was readable through the GitHub connector during this investigation:
  [commit 80fed5c](https://github.com/lbcamargo94/PZ-Rank-Companion/tree/80fed5c1e2a9024e46b737156ad1a8b23ab3ae73),
  with package version `2.7.0`.
- Backend and frontend source were inspected at
  [commit 9f073ad](https://github.com/lbcamargo94/PZ-Rank/tree/9f073ad5e0ae88de11737ac56b908a5c34c7e052).

The Companion binary was not installed or executed, and binary/source
equivalence was not established. No production database, authenticated
submission or moderator action was inspected. Source availability at review
time does not establish the exact deployed version, signing configuration or
how consistently moderators follow the documented process.

### What the mod and Companion actually establish

The installed `RankMain.lua` counts restaurant visits by entering selected room
types and deduplicating building hashes. Its military visit flag comes from
entering a coordinate rectangle. Neither establishes a supplied outpost or
cleared military site. Crafting counters classify recipe names, categories and
tags; they do not establish individual output ownership or storage at a base.
For example, broad `bow` matching can also match `bowl`, and forging categories
can include smelting rather than a finished weapon. No checks for beds, food
calories, barricades, plumbing or a base vehicle were found in this Lua path.

The Companion's [main.js](https://github.com/lbcamargo94/PZ-Rank-Companion/blob/80fed5c1e2a9024e46b737156ad1a8b23ab3ae73/main.js)
watches mod-produced files under `Zomboid/Lua/pz_rank`, reads codes, stats and
other exported records, and uploads them. Its sync path signs codes and stats
with HMAC-SHA256. Local SQLite storage is app history, not evidence of an
independent game-save parser. No independent world, inventory or clearance
verification was found in the reviewed data path. Signing authenticates the
submitted message under the signing scheme; it does not independently prove
that an in-game objective happened.

Companion [local achievements](https://github.com/lbcamargo94/PZ-Rank-Companion/blob/80fed5c1e2a9024e46b737156ad1a8b23ab3ae73/achievements-local.js)
use visit counts for some base achievements, including a threshold of 13 for
all bases. These local indicators are not the backend's official objective
authority: backend achievements instead use the 12 official base records and
moderator-supplied flags.

### Moderator approval and scoring

The [objective editor](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/frontend/src/components/painel/EditObjectivesModal.tsx)
provides a checklist for each of 12 restaurants: base, bed, windows, sink,
power, food, vehicle and arsenal. It also exposes military base, Spiffo HQ and
Spiffo relic flags. The [requirement labels](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/frontend/src/lib/objectives.ts)
specify 12,500 food calories and an arsenal of 20 weapons and 10 tools produced
by the player. These are Brazilian requirements, not agreed TGSRR quantities.

- [PATCH /:id/objectives](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/routes/entries.ts)
  requires moderator access, updates objective data and recomputes the score.
  Player tokens do not grant this authority. The route does not require a VOD
  URL, evidence attachment or review reason, and its object validation is
  shallow rather than a complete checklist schema.
- [Self-moderation protection](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/selfModeration.ts)
  compares the normalized moderator login with the player nickname. This is
  name-based protection rather than a durable account-to-run identity link.
- [Moderation logging](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/moderationLog.ts)
  records the actor, time, action and affected entry/player. Objective edits
  are summarized as changed, without the individual checkbox differences.
- [Scoring](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/scoring.ts)
  awards 1,000 points per official base with `has_base`; it does not require
  all equipment flags for those points. The special flags award military
  1,000, HQ 5,000 and relic 3,000 points.
- [Backend achievements](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/achievements.ts)
  distinguish established bases from visits. Full objective completion
  requires all 12 bases with every equipment flag and all three special
  flags. Military clearance uses the moderator flag, not the visit counter.
- [Sync](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/routes/sync.ts)
  preserves existing approved objectives during a run and clears them for a
  new run. Visit telemetry does not automatically populate approvals.

The [moderation documentation](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/docs/moderacao.md)
records a VOD-based review of base points. This demonstrates a documented human
review practice, not a mandatory evidence gate enforced by the objective API.

### Automated validation and relevance to TGSRR

Backend [Companion stats validation](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/companionStats.ts)
checks allowed fields, numeric bounds, character matching and signatures when
a signing secret is configured. [Plausibility checks](https://github.com/lbcamargo94/PZ-Rank/blob/9f073ad5e0ae88de11737ac56b908a5c34c7e052/backend/src/lib/plausibility.ts)
check kill totals/rates and skill progression, with anomalies subject to review.
These checks add useful validation but do not independently inspect equipment
or prove player crafting provenance.

The useful comparison is automated observations plus human certification in
their system, versus TGSRR's more detailed per-outpost requirement observations,
lifecycle/regression records and reviewable evidence. Neither should be
described as infallible proof of the whole game world. TGSRR's player-crafted
weapon/tool provenance remains pending, as does the approved increase from
5,000 to 20,000 calories per outpost. Our loaded-zombie observation limits also
remain relevant when discussing clearance evidence.

Subsequent TGSRR decision on 19 November: one player-crafted forged crowbar and
one player-crafted forged sledgehammer are mandatory at every outpost. Remaining
equipment and quantities are still being decided; see `IDEAS.md`.
