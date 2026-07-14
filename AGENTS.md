# Project Notes for Codex Agents

This workspace is the source for The Great Spiffo's Rat Race for Project Zomboid.

## Project Memory

Before substantial work, read:

1. `docs/NOW.md` for the single current project focus.
2. Relevant entries in `docs/DECISIONS.md` for settled decisions.
3. `docs/BRAND.md` when writing public-facing names, copy, or visual material.

Use `docs/IDEAS.md` as a parking place, not as approved scope. When a useful idea
arises, capture it there without expanding the current deliverable unless the user
explicitly changes scope.

The project owner has ADHD. Prefer one recommended next action, concise choices,
and progressive disclosure. Avoid presenting large undifferentiated plans unless
requested. When the user says "capture that", record it in the appropriate project
memory document.

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
- Latest decompiled Java reference: `C:\Games\Steam\steamapps\common\ProjectZomboid\zombie_decompiled`
- Legacy decompiled Java reference: `C:\Games\Steam\steamapps\common\PZJava`

## Working Rules

- Prefer `rg` for searches across Lua, Java references, `mod.info`, media scripts, recipes, translations, and workshop dependencies.
- When investigating behavior, search in this order unless the task suggests otherwise:
  1. The Great Spiffo's Rat Race workspace.
  2. Relevant version folders under `Contents/mods/Great Spiffo's Rat Race/`.
  3. Local workshop mods under `C:\Users\refle\Zomboid\Workshop` when code style or established Eurymachus patterns matter.
  4. Steam workshop mods when checking compatibility or comparable mod behavior.
  5. Project Zomboid game files.
  6. Latest decompiled Java references in `ProjectZomboid\zombie_decompiled`.
  7. Legacy decompiled Java references in `PZJava` when legacy comparison is useful.
- Do not edit files outside this mod workspace unless the user explicitly asks for that.
- Use external workshop, local workshop, Project Zomboid, and Java paths as read-only references by default.
- Preserve existing mod structure and Project Zomboid conventions.
- Keep edits focused and avoid unrelated refactors.
