# Reference Collector Research

## Purpose

This document records useful collection techniques found in three unrelated mods. They are research references only.

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

## Additional TGSRR capabilities

The audited versions do not provide authoritative histories for:

- Locations visited and visit times.
- Towns visited and visit times.
- Books and magazines read and read times.
- Loaded-mod session history.

These require TGSRR collectors and stable in-game or TGSRR IDs rather than localized names.

## Storage conclusion

Global ModData and player ModData are serialized save state, not unbounded databases. There is no useful project-level promise that they may be made arbitrarily large. Large nested histories increase save size, serialization cost, load cost, and multiplayer synchronization risk; large player ModData has also proven fragile in practice.

Use ModData for compact authority only:

- Run ID and schema version.
- Last committed sequence/cursor per stream.
- Last known loaded-mod set/hash for delta recovery.
- Small aggregates required by gameplay.

Use character/run-scoped files for append-only or growing histories, with RAM projections for runtime queries and change-only or save-lifecycle writes.
