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
- World-level `ModData` under `TGSRR_OutpostProgress` stores discovery plus normalized last-known deliverable snapshots.
- Persisted deliverables use `available`, `passed`, `current`, `required`, optional presentation `state`, and `observedAt`; transient scan/debug data is excluded.
- A runtime last-written cache prevents unchanged one-second checks from mutating `ModData`.
- Only the outpost containing the player is monitored; there is no remote zombie scan.
- Live outpost deliverables are evaluated on area entry/load, room changes, `OnZombieDead`, and a one-second in-area fallback.
- Fixture deliverables use registered-room reverse lookup, object mutation hooks, and persistent installation ledgers. Good-bed tracking uses `OnObjectAdded` and `OnObjectAboutToBeRemoved` without object scans.
- A lightweight in-process deliverable notification bus refreshes open player-facing views after meaningful record changes; timed UI refresh remains a fallback.
- Recorded generators are resolved only at their persisted XYZ and checked once per second for `isConnected()` and `getFuelPercentage()`; the outpost is not scanned for generators.
- Cached room-object references are invalidated when registered ground-floor rooms unload. A temporarily unstreamed food or sink check is unavailable and must not overwrite its last persisted result; full streaming rebuilds and re-affirms the cache.
- A ten-second in-area grace period prevents clearance certification before instantiated zombies finish loading.

### Ground-floor window survey

- The expected exterior envelope is derived once from the union of registered room rectangles at the outpost sealing level.
- Interior tiles are converted into normalized north/west boundary segments wherever an adjacent tile is outside that union.
- It recognizes `IsoWindow`, `IsoWindowFrame`, and window-type `IsoThumpable` objects.
- Window openings are discovered afresh on those cached boundary segments and inspect barricades on both sides.
- Wood planks, sheet metal, and metal bars are reported as qualifying barricade materials.
- The result is authoritative only when every boundary segment's owning square is loaded.
- The runtime cache stores expected boundary geometry rather than physical window objects, allowing new player-built windows to be detected after walls are demolished.
- A shared per-inspection classification pass identifies walls, windows, door frames, present doors, and door open/closed state for each segment.
- `enclosed` counts segments sealed by a wall, window opening, or present door; an empty door frame is not sealed.
- `doors_fitted` counts present exterior doors against exterior door frames.
- `doors_closed` counts closed exterior doors against the same frame total, so missing doors cannot pass.
- Authoritative aggregate results persist as the outpost's last-known `window_barricades` deliverable.

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
- [MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md](MOD_DECISION_011_OUTPOST_STAGES_AND_CLEARANCE_TRIGGERS.md)
- [MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md](MOD_DECISION_012_OUTPOST_PROGRESS_PERSISTENCE.md)
