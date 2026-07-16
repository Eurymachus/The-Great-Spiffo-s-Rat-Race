# Mod: Outpost Technical Constraints

## Accepted findings

### Building and zone data

- A BuildingDef's coarse rectangle is not the same as the intended outpost complex.
- The manually surveyed core zone is authoritative for selecting the complex; registered BuildingDef IDs provide building/room context.
- One outpost may include multiple surface or underground BuildingDefs.
- The survey tool borrows the animal-zone selection interaction but overrides vanilla's `40x40` livestock-zone limit.

### Room activation

- `RoomDef.doneSpawn` is a public Java field without a Lua-visible getter.
- `RoomDef:isExplored()` is set on the relevant discovery path immediately before room spawning is queued and is the current activation proxy.
- `RoomDef:getIsoRoom()` can persist when physical squares are unloaded.
- A room is treated as currently loaded only when its IsoRoom square list is non-empty.
- Activation persists after squares unload.

### Zombie population

- `IsoCell:getZombieList()` exposes instantiated live zombies without scanning every square.
- Virtual zombies in unloaded areas are retained by the native population manager.
- Normal Lua has no supported arbitrary-area query for those virtual zombies.
- Internal radar data is X/Y-only, private/native, Last Stand/debug-oriented, capped by a fixed Java buffer, and not a supported end-user Lua API.
- `ZombiePopulationRenderer` is exposed for rendering, not programmatic counting.

### Persistence and files

- Debug survey output uses one INI-style record set at `TGSRR/Outposts.ini`; no JSON decoder is required.
- Player-facing clearing/completion persistence is designed but not implemented.

### Zombie kills

- Character Info displays `IsoPlayer:getZombieKills()`.
- The kill value is persisted by the game with the character.
- The tracker uses this value directly and does not maintain a duplicate kill counter.
- `Events.OnZombieDead` is used to refresh the cached record after kills instead of polling the player counter.

## Rejected approaches

- Do not use debug reflection or Last Stand radar behavior for released challenge certification.
- Do not equate `RoomDef:getIsoRoom()` with loaded physical squares.
- Do not use `doneSpawn` directly from Lua.
- Do not continuously scan all `150x150` squares for live zombies; use the cell's zombie list.
- Do not build a duplicate per-zombie registry merely to obtain the current live count; use the game's existing list and persist only challenge session/state data.
- Do not treat a remote `0 loaded rooms` result as proof that an outpost contains zero zombies.

## Engine issue observed during development

A `BufferUnderflowException` occurred inside `ZombiePopulationManager.updateMain()` while native zombie records were read. No tracker code invoked that buffer path. Treat recurrence as an engine/population issue unless new evidence links it to mod behavior.

## Related documents

- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md](MOD_DECISION_005_OUTPOST_SPATIAL_MODEL.md)
- [MOD_DECISION_006_ROOM_ACTIVATION.md](MOD_DECISION_006_ROOM_ACTIVATION.md)
- [MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md](MOD_DECISION_007_LIVE_ZOMBIE_CLEARANCE.md)
- [MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md](MOD_DECISION_010_ZOMBIE_KILL_AUTHORITY.md)
