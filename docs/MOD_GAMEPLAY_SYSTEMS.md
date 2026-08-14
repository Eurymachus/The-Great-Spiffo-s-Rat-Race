# TGSRR Gameplay Systems

This document covers Rat Race gameplay policy implemented outside the challenge
tracker and export contract.

The complete shared Build 42.20 sandbox baseline is recorded in
[`TGSRR_SANDBOX_SETTINGS_B42_20.md`](TGSRR_SANDBOX_SETTINGS_B42_20.md).

## CDDA compatibility

The TGSRR CDDA variant retains the deliberately harder shared Rat Race sandbox,
adds the vanilla CDDA twelve-month apocalypse age and starting-character
injuries, and uses unrestricted Rat Race spawn regions. Build 42.20's revised
fire setup is followed: one explosion is placed in a randomly selected room
excluding kitchens and garages, replacing the legacy five-room loop inherited
from vanilla Build 42.18.

The shared sandbox uses Build 42.20's serialized `MultiplierConfig.Global`
and `GlobalToggle` fields for the intended `0.8` global XP
multiplier. `FirearmUseDamageChance` is the Build 42.20 enum value `2`
(`Zombies only`), retaining chance-to-hit behavior for animals so a valid
aimed shot can still guarantee an animal hit.

The same shared sandbox is shipped as the selectable `Unofficial TGSRR`
Custom Sandbox preset. The unofficial label makes clear that ordinary sandbox
games do not qualify as official tracked Rat Race runs. The preset is loaded
from `media/lua/shared/Sandbox/TGSRR.lua` and applied to a fresh Build 42.20
`SandboxOptions` object through its public option API. This is necessary because
Build 42.20's native `loadGameFile()` resolves only presets in the base game
installation, not active mod files. TGSRR registers the result as a non-user
preset, so it cannot be mistaken for or deleted as a locally saved `.cfg`
preset. The shared Lua sandbox definition is the sole canonical settings
source; automated comparison keeps the shipped preset and challenge runtime
aligned.

## Optional landmark discovery

TGSRR tracks a curated registry of distinctive buildings as optional landmark
discoveries. Landmark membership is keyed by precision-safe `BuildingDef` ID
strings, with an absolute coordinate retained as a validation anchor. A
multi-building site may register several BuildingDefs but still counts as one
landmark.

The client checks the player's current building once per second. The first
entry into a registered landmark records the existing `location.visited`
ledger event, including the landmark ID, BuildingDef ID, discovery method, and
absolute coordinates. The run snapshot exports the registry version,
definition metadata, and first-visit evidence.

Landmarks are shown on their own tracker tab and as an explicitly optional
Overview provider. They do not change the 13 required outposts, contribute to
overall progress, or participate in victory gating. Increasing the landmark
registry version marks older runs partial because visits that happened before
the new definitions were installed cannot be reconstructed reliably.

All registered landmarks and outposts are also added to the vanilla world map
as non-user-defined symbols. Landmarks use the red Asterisk symbol; ordinary
outposts use the blue Cross symbol; Hog Wallow Military Base uses blue
CrossedSwords. Symbols are duplicate-safe and are restored whenever the world
map opens. Selecting a landmark row or the map button in Outpost Overview uses
vanilla's `ISReadWorldMap` timed action before centering the map at a moderate
zoom. Outpost comparison rows themselves retain their normal detail behavior.

## Physical building-visit history

Alongside registered landmark discovery, TGSRR keeps an internal first-entry
record for every BuildingDef physically occupied by the player. The same
one-second observation checks the player's current square, resolves its
IsoBuilding and precision-safe BuildingDef ID, then stores UTC, world age,
in-game calendar/time, and entry coordinates only if that ID has not been seen.

This is intentionally stricter than vanilla `RoomDef.explored`, which can be
set by seeing into a room. It allows a future building-based registry to
reconcile visits made before that registry was added. The building history is
run ModData only and is not included in ledger events or exports. Existing or
bootstrapped histories are marked partial. See
[`MOD_DECISION_018_BUILDING_VISIT_HISTORY.md`](MOD_DECISION_018_BUILDING_VISIT_HISTORY.md).

## Custom alarm decay

Build 42.20 does not expose `BuildingDef.alarmDecay` to Kahlua. When
`TGSRRAlarmDecay.Enabled` is true, TGSRR uses a standalone Lua lifecycle:

1. Vanilla still decides which eligible buildings receive alarms.
2. At `OnLoadedMapZones`, TGSRR snapshots every successful vanilla alarm roll
   as a pending record, assigns and persists its random expiry, and leaves the
   vanilla alarm flag unchanged.
3. Vanilla finishes loading each chunk, including randomized-building stories
   and indoor-zombie population. At `LoadChunk`, TGSRR removes candidates that
   vanilla nullified. Surviving candidates retain their existing expiry between
   `MinimumDay` and `MaximumDay` after electrical shutoff, then TGSRR disables
   Java's automatic per-building trigger without performing another random roll.
4. On a new game, TGSRR removes the pending record for the
   player's starting building and explicitly disarms it before player updates,
   matching vanilla's spawn-building protection.
5. Player entry, window opening, and window smashing check the TGSRR expiry.
6. A live alarm deliberately invokes vanilla's alarm event, retaining its sound
   duration, zombie-attraction world sound, and explored-building effects.
7. For rooms populated later through `OnSeeNewRoom`, TGSRR compares the room's
   zombie population before and after vanilla's immediate `roomSpotted` call.
   A newly populated room removes an already claimed alarm.
8. Pending records remain inert. Only `LoadChunk` processing and its deferred
   retries can claim them; player entry and the debug UI do not force claims.
9. Vanilla `AlarmDecay` is set to 0-1 year as a safety fallback for any alarm
   TGSRR does not claim. It does not affect the initial alarm roll or TGSRR's
   independently stored 0-730 day expiry.

This avoids unsupported Java-field writes while retaining the TGSRR sandbox
variable as the source of the custom battery range.

In debug mode, the alarm window presents the persisted world-wide snapshot.
Unprocessed candidates are labelled `PENDING VANILLA`; teleporting to one
allows vanilla to finish its nullifiers before TGSRR claims or removes it. The
window observes record revisions and refreshes automatically after finalization.
Automatic updates pin the selected building ID instead of rebuilding and
re-sorting the list. A rejected selected candidate remains visible as
`NULLIFIED VANILLA`, preventing the UI from jumping to another building.

## Custom helicopter schedule

When `TGSRRHelicopter.Enabled` is true, TGSRR disables vanilla recurrence and
uses the vanilla helicopter event itself with a persistent TGSRR schedule.
Each configured challenge-year/month slot receives one vanilla-style relative
world-day delay, start hour, and event-window length. Slots are evaluated in
their declared order. The first slot in the challenge's starting month is
anchored to world day zero; later slots are anchored to the challenge's start
day-of-month in their configured calendar month. For a July 9 challenge start,
each later slot begins on the 9th of its configured month.

The default Rat Race schedule is:

| Challenge year | Calendar months |
|---|---|
| 1 | July |
| 2 | July, January |
| 3 | July, November, March |
| 4 | July, October, January, April |
| 5 | July, September, November, January, March |
| 6 | July, October, January, April |
| 7 | July, November, March |
| 8 | July, January |
| 9 | July |

The default delay uses vanilla's `Rand.Next(6, 10)` behavior, so an event is
scheduled 6, 7, 8, or 9 world days after its slot begins. The start-hour range
is 09:00 through 18:00, and the event-window range is one through four hours.
Scheduler state is stored in global ModData under
`TGSRR_HelicopterScheduler`; a loaded game therefore retains the selected slot
and does not reroll it every session.

For the default July 9 challenge start, every configured month is anchored to
its 9th day. The default delay therefore schedules each event on the 15th,
16th, 17th, or 18th. For example, the Year 2 July slot is anchored to July 9
of Year 2 and schedules an event from July 15 through July 18. January and
other configured months use the same 9th-day anchor.

`DayMaximum` is an exclusive bound so the settings mirror vanilla directly:
`DayMinimum = 6` and `DayMaximum = 10` produce 6 through 9. The configured
duration values describe the period during which vanilla may activate the
event. They do not change the helicopter's airborne duration, which remains
controlled by the vanilla helicopter state machine.

The registered sandbox settings expose the enable switch, yearly comma-separated
month lists, and the shared date/time ranges. In debug mode, the TGSRR
Helicopter window displays the active schedule and can jump to its date for
testing.

## Custom ranch mortality

When `TGSRRRanchMortality.Enabled` is true, TGSRR intercepts vanilla `Ranch`
meta-zones before vanilla ranch population and temporarily identifies them as
`TGSRR_Ranch`. Once a controlled zone is fully streamed, TGSRR performs the
vanilla-compatible ranch chance and population process exactly once, creates or
reuses its livestock designation, and persists the result under
`TGSRR_RanchControl`.

Adjacent ranch rectangles are treated as one logical ranch so split map zones
cannot independently duplicate their population. Spawned females, males, and
babies use the vanilla ranch definitions; only the mortality decision is
replaced.

Mortality begins after `RollStartDay`. For each adult, the roll remains the
vanilla-shaped `1 / (deathDay - worldAgeDays)` chance, becoming guaranteed at
the configured sex-specific death day. A death day of `-1` disables mortality
for that sex. The Rat Race defaults retain the vanilla roll start of day 60 but
set both female and male death days to `-1`.

When custom mortality is disabled, TGSRR restores controlled zones to vanilla
`Ranch` and leaves population to the game. The seven-month challenge variant is
a test surface for reaching ranch-age boundaries quickly; it is not a separate
export contract.

## Validation

The pure Lua tests cover CDDA's Build 42.20 fire and sandbox compatibility;
helicopter date conversion, scheduling and runtime ownership; ranch mortality
boundaries, zone interception, one-time spawning, adjacent-zone grouping, and
runtime enable/disable behavior; and the seven-month challenge definition.
