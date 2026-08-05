# TGSRR - Level Up

## Status

Parked design proposal. This document records the agreed concept and balance
target. It does not describe an implemented or leaderboard-approved challenge.

## Concept

Players retain every skill level supplied by their chosen character build. Each
subsequent skill level is locked until the player:

1. Earns the normal Project Zomboid XP required for that level.
2. Pays kill credits equal to that level's normal XP requirement.

Every player-attributed zombie kill awards one kill credit. Kill credits are a
separate spendable balance and do not reduce the character's displayed total
zombie kills when spent.

## Banked XP

XP earned toward a locked level is retained. When the XP requirement is met,
the skill remains at its current level and waits for payment. XP does not
continue into the following level while the current level remains locked.

The player can satisfy the payment with ordinary kill credits, including bonus
kill credits awarded by milestones. Milestone credits never waive the XP
requirement.

## Kill Milestones

The proposed milestones award universal bonus kill credits. They spend exactly
like credits earned from kills and may be used on any skill.

| Total zombie kills | Bonus kill credits |
| ---: | ---: |
| 1,000 | 1,500 |
| 10,000 | 6,000 |
| 25,000 | 12,000 |
| 50,000 | 21,000 |
| 100,000 | 50,000 |
| 250,000 | 100,000 |
| 500,000 | 150,000 |
| 750,000 | 250,000 |
| 990,000 | 350,000 |
| **Total** | **940,500** |

Credits rather than level-specific unlocks ensure that milestone rewards remain
useful for characters with different starting skill levels.

## Outpost Rewards

Each of the 13 completed outposts awards one free non-physical level unlock.
The reward:

- Bypasses both the XP requirement and kill-credit cost.
- May be used only for the character's next level in a skill.
- Cannot be used on Strength or Fitness.
- Is retained until the player chooses to spend it.

The Strength and Fitness restriction prevents an outpost from bypassing the
largest passive-skill XP requirements. Outposts remain valuable for slow or
otherwise inconvenient non-physical skills.

## Theoretical Balance Target

The calculation below assumes the maximum-cost case: all 35 tracked skills
start at level 0, all 13 outpost rewards are spent optimally, all milestone
credits are earned, and every remaining level is purchased with kill credits.

Build 42.20 requires 32,775 XP for each of the 33 ordinary skills to advance
from level 0 to level 10. Strength and Fitness each require 487,500 XP.

```text
33 ordinary skills x 32,775 XP    1,081,575
Strength and Fitness x 487,500      975,000
                                      -------
All 35 skills                     2,056,575

13 optimal non-physical outposts   -117,000
Milestone bonus kill credits       -940,500
                                      -------
Actual kills required               999,075
```

At 990,000 kills, the player receives the final 350,000 bonus credits. The
theoretical all-zero run then requires another 9,075 kills and completes 925
kills below one million.

Characters with starting skill levels require fewer kills because their build
has already paid part of the total skill progression cost. The 999,075 figure
is therefore a theoretical maximum for a zero-to-hero character, not a fixed
completion target for every build.

## Parked Implementation Considerations

- Add a distinct challenge definition and identity, provisionally named
  `TGSRR_LevelUp` and displayed as `The Great Spiffo's Rat Race - Level Up`.
- Capture awarded XP safely after Build 42 applies it, reverse locked XP under
  a recursion guard, and retain the exact awarded amount in an escrow balance.
- Release only the XP needed for the purchased level and prevent escrowed XP
  from advancing into a second locked level.
- Track total earned, milestone-awarded, spent, and available kill credits
  separately from the character's total zombie kills.
- Record milestone awards, outpost awards, credit spending, and level unlocks
  in the run ledger so save rollback cannot duplicate rewards.
- Export the complete credit, escrow, reward, and purchase state with the run.
- Provide a player-facing view of current level, banked XP, required XP,
  available credits, price, and applicable outpost rewards.
- Verify Strength, Fitness, trait XP modifiers, skill books, recipes, passive
  stat effects, death, save/load, and rollback behavior in game.

