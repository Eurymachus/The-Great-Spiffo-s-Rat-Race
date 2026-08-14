# Decision 013: Outpost progress weights

## Status

Accepted during tracker development.

## Decision

Each outpost has a weighted player-facing progress score:

| Deliverable | Weight |
| --- | ---: |
| Discovery | 2% |
| Room activation | 8% |
| Floor activation | 4% |
| Zombie clearance | 15% |
| Window barricades | 10% |
| Enclosed | 10% |
| Doors fitted | 5% |
| Doors closed | 3% |
| Good bed | 6% |
| Generator | 8% |
| Food | 8% |
| Sink | 8% |
| Spare car | 10% |
| Spare car started (latched) | 3% |

Ratio-based requirements award capped partial credit. Discovery, zombie clearance, good bed, sink, and successful engine start are binary. Generator partial credit requires a connected generator and follows its fuel percentage. Spare-car partial credit follows the proportion of inspected component requirements currently satisfied.

An outpost is **Complete** only when every required deliverable passes. The weighted percentage does not independently grant completion.

The Overview outpost percentage is the arithmetic mean of the 14 individual percentages. Its count is the number of strictly Complete outposts out of 13.
