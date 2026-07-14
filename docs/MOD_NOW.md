# Mod: Current Focus

## Branch and worktree

- Development branch: `codex/outpost-tracker-dev`
- Live challenge branch: `master`
- Project Zomboid loads the main mod worktree, so switch it to `master` before continuing an active run and back to the development branch for tracker work.
- Website development is isolated in its own worktree on `codex/website-dev`.

## Current deliverable

Build a modular, player-facing Rat Race Challenge Tracker whose registered modules appear as tabs across the top. The first module is **Outposts**.

## Implemented

- Generic `TGSRR.ChallengeTracker.registerModule()` registry.
- Persistent, resizable tabbed tracker window.
- Player-facing tracker enabled for `TGSRR`, `TGSRR_CDDA`, and `TGSRR_Sprinters` challenges.
- Outposts tab with one compact progress bar per outpost.
- Outpost name and percentage rendered inside each bar.
- Hover tooltip with current activation/building data.
- One-second refresh while the Outposts tab is visible.
- Existing debug Inspector opens on double-click as a temporary placeholder for the future Outpost Overview.
- Left-edge, vertically centred tracker launcher using `media/ui/TGSRR/tgsrr.png` is implemented but not yet tested in game.
- Debug survey, zone editor, teleport controls, inspector, outpost definitions/API, world resolver, and room-activation check.
- Decorative inaccessible tower RoomDefs are excluded for known affected outposts.

## Important current limitations

- Tracker completion currently equals required-room activation only. It can misleadingly show `100/100%` before an outpost satisfies the complete challenge requirements.
- Live zombie-clearing sessions are designed but not implemented.
- Normal Lua cannot authoritatively query virtual zombies in unloaded areas. While a player is clearing an outpost, use `getCell():getZombieList()` as the authoritative live instantiated-zombie source within the configured 150x150 clearance bounds, then persist the achieved clearing state.
- The debug Inspector is not the final player-facing Outpost Overview.
- Security and habitation checks are not implemented yet.

## Settled outpost rules relevant to implementation

- Clearance area: configured 150x150 bounds around the outpost anchor.
- Every relevant accessible room and basement must activate.
- Ground floor only: every exterior window needs at least one wood or metal barricade; exterior doorways need a repaired/replaced door; exterior walls must be sealed.
- Other completion requirements: good bed, power, at least 5000 calories of food, plumbed sink, and spare car near the outpost.
- Distinguish **Cleared** (activation complete and live zombie count reaches zero during an authoritative visit) from **Completed** (cleared plus all deliverables pass).

## Recommended next action

Test the new left-edge icon launcher in game. Once its placement and scale are accepted, implement the runtime outpost clearing controller and feed its exact in-zone zombie count/state into the existing Outposts module.
