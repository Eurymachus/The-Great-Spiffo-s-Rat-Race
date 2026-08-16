# MOD Decision 002: Overview Shows Aggregate Deliverables

- Status: Accepted
- Date: 2026-07-16

## Context

The first Overview implementation repeated every outpost and its percentage. This duplicated the Outposts tab and implied that Overview needed an extremely large window to accommodate all future detailed data.

## Decision

Overview will show one summary for each challenge deliverable category. It will not list every underlying outpost or record.

For outposts, Overview shows:

- Currently Completed outposts out of 13.
- Overall progress equal to the sum of all 13 individual outpost percentages divided by `1300%` (the arithmetic mean).

Partial outpost progress contributes to the percentage without contributing to the completed count. For example, three outposts at `100%` produce `3/13` and approximately `23%`; three outposts at `50%` produce `0/13` and approximately `11.5%`.

Individual outposts and diagnostic values belong on the Outposts tab.
Inspector-level checks belong in the outpost detail view. Individual outpost
percentages use the accepted weighted formula in Decision 013.

The Overview footer uses the public challenge weighting: Kills provide 50%,
Outposts provide 25%, and Skills provide 25%. Optional categories remain
visible but do not affect that figure. Landmarks are currently optional. If a
required category is unavailable, the available weights are normalized in the
same way as the website leaderboard calculation.

## Consequences

- Overview remains readable as more deliverable categories are added.
- The tracker can remain substantially smaller than the earlier `1120x1000` prototype; the current implementation is `800x650`.
- Detailed tabs become the authoritative comparison views.
- Each system must expose a stable aggregate deliverable record.
- The in-game headline percentage matches the website's public leaderboard
  weighting without making the mod's combined value authoritative.
- The aggregate outpost formula is settled. Individual outpost percentages use
  the accepted weighted formula in Decision 013.

## Related documents

- [MOD_TRACKER.md](MOD_TRACKER.md)
- [MOD_OUTPOSTS.md](MOD_OUTPOSTS.md)
- [MOD_DECISION_001_TRACKER_ARCHITECTURE.md](MOD_DECISION_001_TRACKER_ARCHITECTURE.md)
- [MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md](MOD_DECISION_004_OUTPOST_CLEARING_AND_COMPLETION.md)
