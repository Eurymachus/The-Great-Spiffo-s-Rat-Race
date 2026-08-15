# Project Notes for Codex Agents

This workspace is the source for The Great Spiffo's Rat Race for Project Zomboid.

## Project Memory

Before substantial work, identify the workstream and read its current-focus
document when that document exists on the current branch:

- Website/platform work: `docs/WEBSITE_NOW.md`
- Project Zomboid mod work: `docs/MOD_NOW.md`

Also read relevant entries in `docs/DECISIONS.md` for settled project-wide
decisions, and `docs/BRAND.md` when writing public-facing names, copy, or visual
material. A workstream document may legitimately be absent from a development
branch that predates it. Do not search or edit a sibling worktree merely to find
the missing document; use the current branch's instructions and code instead.

Use `docs/IDEAS.md` as a parking place, not as approved scope. When a useful idea
arises, capture it there without expanding the current deliverable unless the user
explicitly changes scope.

The project owner has ADHD. Prefer one recommended next action, concise choices,
and progressive disclosure. Avoid presenting large undifferentiated plans unless
requested. When the user says "capture that", record it in the appropriate project
memory document.

## Workspace

- Canonical development branch: `codex/rat-race-dev`
- Canonical local worktree: `E:\LocalProfiles\Eurymachus\GameData\Zomboid\Workshop\The Great Spiffo's Rat Race`
- Primary editable mod content lives under `Contents/`.
- Mod versions currently live under `Contents/mods/Great Spiffo's Rat Race/`.
- Website and mod changes are authored together in this worktree.

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

## Website Startup

- When asked to start, spin up, restart, or run the local website, always use
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_website_dev.ps1" -Port 8001 -Background`
  from the repository root.
- Never start the local website with a bare `manage.py runserver`. The canonical
  launcher loads `.env`, starts the reference-update worker, and verifies both
  services.
- Before reporting the website as ready, confirm an HTTP 200 response and one
  logical `run_reference_update_worker` process tree.

## Project Zomboid Lua Restrictions

- Before relying on a Java class, method, field, constructor, or global from
  shipped Lua, verify that it is actually exposed through Project Zomboid's
  Kahlua bridge. A public Java API in the decompile is not sufficient proof.
  For the current build, inspect `zombie.Lua.LuaManager.Exposer`: classes must
  be admitted by its `setExposed(...)` list (directly or through an exposed
  type), and callable members must be public and not marked `@HiddenFromLua`.
  Lua globals are generally methods registered from
  `LuaManager.GlobalObject`, commonly with `@LuaMethod(global = true)`, or by
  another explicit `register`/exposure path. `@UsedFromLua` is useful evidence
  of intended Lua use, but do not treat that annotation alone as proof that a
  particular member is callable. Confirm against `LuaManager.Exposer`, an
  established vanilla Lua call site, or an in-game probe before designing
  around the API.
- Project Zomboid's restricted Kahlua environment does **not** expose the
  standard Lua `next()` global. Never use `next(table)` in shipped mod Lua.
  Test table emptiness with a `pairs()` loop instead.
- Desktop Lua tests do not reproduce every missing Kahlua global. Before
  handing off Lua changes, run:
  `rg -n "\bnext\s*\(" "Contents/mods/Great Spiffo's Rat Race" --glob "*.lua"`
  and require zero matches.
