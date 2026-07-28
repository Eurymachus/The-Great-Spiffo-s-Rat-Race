# TGSRR Gameplay Systems

This document covers Rat Race gameplay policy implemented outside the challenge
tracker and export contract.

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

The pure Lua tests cover helicopter date conversion, scheduling and runtime
ownership; ranch mortality boundaries, zone interception, one-time spawning,
adjacent-zone grouping, and runtime enable/disable behavior; and the seven-month
challenge definition.
