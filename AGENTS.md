# Project Notes for Codex Agents

This workspace is the source for The Great Spiffo's Rat Race for Project Zomboid.

## Workspace

- Mod workspace: `E:\LocalProfiles\Eurymachus\GameData\Zomboid\Workshop\The Great Spiffo's Rat Race`
- Primary editable mod content lives under `Contents/`.
- Mod versions currently live under `Contents/mods/Great Spiffo's Rat Race/`.
- Treat this workspace as the normal place to make changes.

## Reference Paths

Use these local paths when tracing Lua behavior, mod dependencies, or Project Zomboid internals:

- Steam workshop mods: `C:\Games\Steam\steamapps\workshop\content\108600`
- Local workshop mods / style references: `C:\Users\refle\Zomboid\Workshop`
- Project Zomboid install: `C:\Games\Steam\steamapps\common\ProjectZomboid`
- Versioned decompiled Java root: `C:\Games\Steam\steamapps\common\ProjectZomboid\tgsrr_decompiled`
- Legacy decompiled Java reference: `C:\Games\Steam\steamapps\common\PZJava`

### Authoritative Decompiled Java Selection

- Treat the versioned directories under `tgsrr_decompiled` as the source of
  truth for current Project Zomboid Java code. Do not use
  `ProjectZomboid\zombie_decompiled` as a current reference.
- Directory names follow `build-<SteamBuildId>-job-<jobId>`. The Steam build
  ID identifies the exact Project Zomboid binary build; the job ID identifies
  the website decompilation run.
- Select a directory whose `.tgsrr-build-id` matches the currently installed
  Steam build ID. When multiple successful directories exist for that build,
  use the one with the greatest numeric job ID.
- For the currently installed Build 42.20 / Steam build `24449119`, the
  authoritative reference is:
  `C:\Games\Steam\steamapps\common\ProjectZomboid\tgsrr_decompiled\build-24449119-job-5`
- Continue to use `C:\Games\Steam\steamapps\common\PZJava` only when legacy
  behavior or API mapping is useful.

## Working Rules

- Prefer `rg` for searches across Lua, Java references, `mod.info`, media scripts, recipes, translations, and workshop dependencies.
- When investigating behavior, search in this order unless the task suggests otherwise:
  1. The Great Spiffo's Rat Race workspace.
  2. Relevant version folders under `Contents/mods/Great Spiffo's Rat Race/`.
  3. Local workshop mods under `C:\Users\refle\Zomboid\Workshop` when code style or established Eurymachus patterns matter.
  4. Steam workshop mods when checking compatibility or comparable mod behavior.
  5. Project Zomboid game files.
  6. The matching authoritative versioned Java decompile under
     `ProjectZomboid\tgsrr_decompiled`.
  7. Legacy decompiled Java references in `PZJava` when legacy comparison is useful.
- Do not edit files outside this mod workspace unless the user explicitly asks for that.
- Use external workshop, local workshop, Project Zomboid, and Java paths as read-only references by default.
- Preserve existing mod structure and Project Zomboid conventions.
- Keep edits focused and avoid unrelated refactors.

## Project Zomboid Lua Restrictions

- Project Zomboid's restricted Kahlua environment does **not** expose the
  standard Lua `next()` global. Never use `next(table)` in shipped mod Lua.
  Test table emptiness with a `pairs()` loop instead.
- Desktop Lua tests do not reproduce every missing Kahlua global. Before
  handing off Lua changes, run:
  `rg -n "\bnext\s*\(" "Contents/mods/Great Spiffo's Rat Race" --glob "*.lua"`
  and require zero matches.
