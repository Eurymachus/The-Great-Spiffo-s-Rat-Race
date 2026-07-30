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

## Custom helicopter schedule

When `TGSRRHelicopter.Enabled` is true, TGSRR disables vanilla recurrence and
uses the vanilla helicopter event itself with a persistent TGSRR schedule.
Each configured challenge-year/month slot receives one randomly selected
calendar day, start hour, and duration from the configured inclusive ranges.
Slots are evaluated in their declared order and dates are calculated from the
world's actual challenge start date.

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

The default day range is the 8th through 14th, the start-hour range is 09:00
through 18:00, and the duration range is one through four hours. Scheduler state
is stored in global ModData under `TGSRR_HelicopterScheduler`; a loaded game
therefore retains the selected slot and does not reroll it every session.

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
