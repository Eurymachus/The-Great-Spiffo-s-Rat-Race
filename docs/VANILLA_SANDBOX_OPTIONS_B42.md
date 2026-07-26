# Vanilla Project Zomboid sandbox options — Build 42.19

> Generated and then reviewed against the locally installed **42.19** runtime registry. This is a decision reference, not a replacement for the game code. Project Zomboid is under active development, so re-audit after an update.

## How to read this reference

The canonical registry contains **269 vanilla options**. Every registered raw ID appears exactly once below. “Code default” is the constructor fallback, not necessarily the value selected by Apocalypse, Survivor, Builder, or a server preset. Enum numbers are serialized values; named values are included where the English translation catalogue defines them.

The **Code effect** column combines the vanilla tooltip with implementation tracing. “Related / gated by” means either a hard gate, a derived-value relationship, or a multiplier that participates in the same calculation; it does not always mean both settings must be enabled.

### Important interaction rules

- High-level `Zombies` and `ZombieRespawn` controls are convenience selectors. Advanced `ZombieConfig.*` values are the operative population/respawn parameters after presets are loaded.
- Loot is layered: distribution rolls × `RollsMultiplier` × category rarity × local/population effects, followed by pre-looted/diminishing/removal rules. Setting one category to zero does not change story or zombie loot unless their dedicated removal controls apply.
- Loot respawn is completely off when `HoursForLootRespawn = 0`; its seen-hours, max-items, and construction guards then have nothing to govern.
- Exact shutoff modifier fields override/randomisation behaviour associated with their high-level enum. A modifier of `-1` delegates back to the enum.
- `FuelStationGasInfinite` overrides finite reserve bounds and empty chance.
- XP has several layers: base `XPmultiplier`, `XPBoost`, global/per-skill `MultiplierConfig.*`, plus profession/trait and literature bonuses.
- Many world-generation settings only affect newly generated or not-yet-seen cells/buildings/vehicles. Changing them cannot reliably rewrite already-generated world state.

## Loot-age mechanisms: exact Build 42.19 calculations

These are two separate systems. **Pre-looted/trashed buildings** choose and transform a whole building through randomized-building stories. **Diminished generated loot** reduces ordinary item-generation probability in containers. Enabling one does not enable the other.

### Shared apocalypse-age input

Both calculations start with:

```text
ElapsedApocalypseDays = floor(GameTime.worldAgeHours / 24)
                     + ((TimeSinceApo - 1) * 30)
EffectiveElapsedApocalypseDays = max(1, ElapsedApocalypseDays)
```

`TimeSinceApo` therefore contributes a 30-day offset for every enum step after its first value. The minimum effective day is 1, so an enabled ramp begins slightly above zero rather than at exactly zero.

### Pre-looted and trashed building calculation

The base value returned by `SandboxOptions.getCurrentLootedChance(IsoGridSquare)` is:

```text
if MaximumLooted <= 0:
    CurrentLootedChance = 0
else if DaysUntilMaximumLooted <= 0:
    CurrentLootedChance = MaximumLooted
else:
    LootedRampDay = min(EffectiveElapsedApocalypseDays, DaysUntilMaximumLooted)
    CurrentLootedChance = floor(MaximumLooted * LootedRampDay
                                / DaysUntilMaximumLooted)
```

When an `IsoGridSquare` is supplied, Build 42.19 then applies:

```text
if ItemPickerJava.getSquareRegion(IsoGridSquare) == null:
    CurrentLootedChance = CurrentLootedChance * floor(RuralLooted)

if IsoGridSquare.getSquareZombiesType() == "Rich":
    CurrentLootedChance = floor(CurrentLootedChance * 1.5)

if CurrentLootedChance <= 0:
    CurrentLootedChance = 1
```

Consequences:

- `RuralLooted` is stored as a double but cast to an integer: values from 0.0 through 0.999… multiply by 0, values from 1.0 through 1.999… multiply by 1, and 2.0 multiplies by 2. Because the final positive-setting floor is 1, a rural result reduced to 0 becomes 1 rather than disabling the story.
- `MaximumLootedBuildingRooms` is checked separately. `RBLooted` and `RBTrashed` reject the entire building when its room count is greater than `MaximumLootedBuildingRooms`; they do not process only the first N rooms.
- `RBShopLooted` accepts a real shop before reaching its non-shop room-count check, so the room ceiling principally governs houses/trashed buildings and non-shop candidates.
- The computed value is consumed as the dynamic chance for the **Trashed Building** story and as a severity/eligibility input by related randomized-building stories. It is not itself a universal per-building dice roll applied to every building type.

### Diminished generated-loot calculation

`SandboxOptions.getCurrentDiminishedLootPercentage(IsoGridSquare)` calculates:

```text
if MaximumDiminishedLoot <= 0:
    CurrentDiminishedLootPercentage = 0
else if DaysUntilMaximumDiminishedLoot <= 0:
    CurrentDiminishedLootPercentage = MaximumDiminishedLoot
else:
    DiminishedRampDay = min(EffectiveElapsedApocalypseDays,
                            DaysUntilMaximumDiminishedLoot)
    CurrentDiminishedLootPercentage =
        floor(MaximumDiminishedLoot * DiminishedRampDay
              / DaysUntilMaximumDiminishedLoot)

if ItemPickerJava.getSquareRegion(IsoGridSquare) == null:
    CurrentDiminishedLootPercentage =
        CurrentDiminishedLootPercentage * floor(RuralLooted)

CurrentDiminishedLootPercentage =
    clamp(CurrentDiminishedLootPercentage, 0, 100)

CurrentLootMultiplier =
    1.0 - (CurrentDiminishedLootPercentage / 100.0)
```

`ItemPickerJava` applies that multiplier after the item's base chance, category loot modifier, and zombie-density addition have been combined:

```text
FinalItemSpawnChance =
    ((BaseItemChance * 100 * CategoryLootModifier)
      + AdjustedZombieDensity)
    * CurrentLootMultiplier
```

Thus `MaximumDiminishedLoot = 20` eventually multiplies the combined chance by 0.80; `MaximumDiminishedLoot = 100` reduces it to zero. In a rural square, `RuralLooted = 2.0` doubles the diminished percentage before the 100% clamp. Unlike the pre-looted calculation, a fractional `RuralLooted` cast to 0 leaves the diminished percentage at 0.

## Complete option catalogue

### Population

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Zombie Count**<br>`Zombies` | enum 1–6; code default `4`; Apocalypse `4` | Convenience population selector. Loading/conversion code maps it to `ZombieConfig.PopulationMultiplier`; the advanced multiplier is the operative density value. Values: 1=Insane; 2=Very High; 3=High; 4=Normal; 5=Low; 6=None. | Independent/no hard gate identified |
| **Zombie Distribution**<br>`Distribution` | enum 1–2; code default `1`; Apocalypse `1` | Selects urban-focused population-map density or uniform density. Values: 1=Urban Focused; 2=Uniform. | Independent/no hard gate identified |
| **Voronoi Noise**<br>`ZombieVoronoiNoise` | boolean; code default `true`; Apocalypse `true` | Controls whether some randomization is applied to zombie distribution. | Independent/no hard gate identified |
| **Zombie Respawn**<br>`ZombieRespawn` | enum 1–4; code default `2`; Apocalypse `4` | High-level respawn selector used to derive advanced respawn values; the `ZombieConfig.Respawn*` fields contain the operative timing and fraction. Values: 1=High; 2=Normal; 3=Low; 4=None. | Independent/no hard gate identified |
| **Zombie Migration**<br>`ZombieMigrate` | boolean; code default `true`; Apocalypse `true` | Zombie allowed to migrate to empty cells. | Independent/no hard gate identified |

### Advanced zombie population

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Population Multiplier**<br>`ZombieConfig.PopulationMultiplier` | double 0.0–4.0; code default `0.65f`; Apocalypse `0.65` | Base zombie density multiplier applied to the map's population values. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Population Start Multiplier**<br>`ZombieConfig.PopulationStartMultiplier` | double 0.0–4.0; code default `1.0`; Apocalypse `1.0` | Multiplier at world start, interpolated toward `PopulationPeakMultiplier` by `PopulationPeakDay`. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Population Peak Multiplier**<br>`ZombieConfig.PopulationPeakMultiplier` | double 0.0–4.0; code default `1.5`; Apocalypse `1.5` | Target population multiplier reached on `PopulationPeakDay`. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Population Peak Day**<br>`ZombieConfig.PopulationPeakDay` | integer 1–365; code default `28`; Apocalypse `28` | World day on which the peak multiplier is reached. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Respawn Hours**<br>`ZombieConfig.RespawnHours` | double 0.0–8760.0; code default `72.0`; Apocalypse `0.0` | Hours between zombie respawn checks. `0` disables respawn and makes the other respawn fields ineffective. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Respawn Unseen Hours**<br>`ZombieConfig.RespawnUnseenHours` | double 0.0–8760.0; code default `16.0`; Apocalypse `0.0` | A chunk must remain unseen for this many hours before respawn is allowed. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Respawn Multiplier**<br>`ZombieConfig.RespawnMultiplier` | double 0.0–1.0; code default `0.1`; Apocalypse `0.0` | Fraction of the desired population restored per respawn cycle. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Redistribute Hours**<br>`ZombieConfig.RedistributeHours` | double 0.0–8760.0; code default `12.0`; Apocalypse `12.0` | Hours between migration/redistribution updates. `0` disables redistribution; high-level `ZombieMigrate` may also disable it. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Follow Sound Distance**<br>`ZombieConfig.FollowSoundDistance` | integer 10–1000; code default `100`; Apocalypse `100` | Maximum tile distance zombies use when pursuing an emitted sound; this governs hearing response after a sound exists, while lore hearing affects detection. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Rally Group Size**<br>`ZombieConfig.RallyGroupSize` | integer 0–1000; code default `20`; Apocalypse `20` | Target zombie count per rally group. `0` disables rally grouping. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Rally Group Size Variance**<br>`ZombieConfig.RallyGroupSizeVariance` | integer 0–100; code default `50`; Apocalypse `50` | Percentage variance around `RallyGroupSize`, preventing every group from having the same target size. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Rally Travel Distance**<br>`ZombieConfig.RallyTravelDistance` | integer 5–50; code default `20`; Apocalypse `20` | Maximum distance zombies travel to form a rally group. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Rally Group Separation**<br>`ZombieConfig.RallyGroupSeparation` | integer 5–25; code default `15`; Apocalypse `15` | Minimum spacing the population manager tries to maintain between rally groups. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Rally Group Radius**<br>`ZombieConfig.RallyGroupRadius` | integer 1–10; code default `3`; Apocalypse `3` | Radius within which members spread around their rally-group centre. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |
| **Zombie count before deletion**<br>`ZombieConfig.ZombiesCountBeforeDelete` | integer 10–500; code default `300`; Apocalypse `300` | How many zombies can occupy a certain area. | `Zombies`, `ZombieRespawn`, `ZombieMigrate` |

### Zombie lore and behaviour

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Speed**<br>`ZombieLore.Speed` | enum 1–4; code default `2`; Apocalypse `4` | How fast zombies move. Values: 1=Sprinters; 2=Fast Shamblers; 3=Shamblers; 4=Random. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Random Sprinter Amount**<br>`ZombieLore.SprinterPercentage` | integer 0–100; code default `33`; Apocalypse `0` | If Random Speed is enabled, this controls what percentage of zombies are Sprinters. Check the "Advanced" box below to use a custom percentage. | `Zombies`, `ZombieConfig.PopulationMultiplier`, `ZombieLore.Speed` |
| **Strength**<br>`ZombieLore.Strength` | enum 1–4; code default `2`; Apocalypse `2` | The damage zombies inflict per attack. Values: 1=Superhuman; 2=Normal; 3=Weak; 4=Random. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Toughness**<br>`ZombieLore.Toughness` | enum 1–4; code default `2`; Apocalypse `4` | The difficulty of killing a zombie. Values: 1=Tough; 2=Normal; 3=Fragile; 4=Random. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Transmission**<br>`ZombieLore.Transmission` | enum 1–4; code default `1`; Apocalypse `1` | How the Knox Virus spreads. Values: 1=Blood and Saliva; 2=Saliva Only; 3=Everyone's Infected; 4=None. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Infection Mortality**<br>`ZombieLore.Mortality` | enum 1–7; code default `5`; Apocalypse `5` | How quickly the infection takes effect. Values: 1=Instant; 2=0-30 Seconds; 3=0-1 Minutes; 4=0-12 Hours; 5=2-3 Days; 6=1-2 Weeks; 7=Never. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Reanimate Time**<br>`ZombieLore.Reanimate` | enum 1–6; code default `3`; Apocalypse `3` | How quickly infected corpses rise as zombies. Values: 1=Instant; 2=0-30 Seconds; 3=0-1 Minutes; 4=0-12 Hours; 5=2-3 Days; 6=1-2 Weeks. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Cognition**<br>`ZombieLore.Cognition` | enum 1–4; code default `3`; Apocalypse `3` | Zombie intelligence. Values: 1=Navigate and Use Doors; 2=Navigate; 3=Basic Navigation; 4=Random. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Random Door Opening Amount**<br>`ZombieLore.DoorOpeningPercentage` | integer 0–100; code default `33`; Apocalypse `0` | When cognition is Random, percentage of zombies assigned the ability to open doors; otherwise cognition determines the behaviour directly. | `Zombies`, `ZombieConfig.PopulationMultiplier`, `ZombieLore.Cognition` |
| **Crawl Under Vehicle**<br>`ZombieLore.CrawlUnderVehicle` | enum 1–7; code default `5`; Apocalypse `5` | How often zombies can crawl under parked vehicles. Values: 1=Crawlers Only; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Memory**<br>`ZombieLore.Memory` | enum 1–6; code default `2`; Apocalypse `2` | How long zombies remember a player after seeing or hearing them. Values: 1=Long; 2=Normal; 3=Short; 4=None; 5=Random; 6=Random between Normal and None. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Sight**<br>`ZombieLore.Sight` | enum 1–5; code default `2`; Apocalypse `5` | Zombie vision radius. Values: 1=Eagle; 2=Normal; 3=Poor; 4=Random; 5=Random between Normal and Poor. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Hearing**<br>`ZombieLore.Hearing` | enum 1–5; code default `2`; Apocalypse `5` | Zombie hearing radius. Values: 1=Pinpoint; 2=Normal; 3=Poor; 4=Random; 5=Random between Normal and Poor. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **New Stealth System**<br>`ZombieLore.SpottedLogic` | boolean; code default `true`; Apocalypse `true` | Activates the new advanced stealth mechanics, which allows you to hide from zombies behind cars, takes traits and weather into account, and much more. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Environmental Attacks**<br>`ZombieLore.ThumpNoChasing` | boolean; code default `false`; Apocalypse `false` | If zombies that have not seen/heard player can attack doors and constructions while roaming. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Damage Construction**<br>`ZombieLore.ThumpOnConstruction` | boolean; code default `true`; Apocalypse `true` | If zombies can destroy player constructions and defenses. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Day/Night Zombie Speed Effect**<br>`ZombieLore.ActiveOnly` | enum 1–3; code default `1`; Apocalypse `1` | Whether zombies are more "active" during the day or night. "Active" zombies will use the speed set in the "Speed" setting. "Inactive" zombies will be slower, and tend not to give chase. Values: 1=Both; 2=Night; 3=Day. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Zombie House Alarm Triggering**<br>`ZombieLore.TriggerHouseAlarm` | boolean; code default `false`; Apocalypse `true` | If zombies trigger house alarms when breaking through windows or doors. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Drag Down**<br>`ZombieLore.ZombiesDragDown` | boolean; code default `true`; Apocalypse `true` | If multiple attacking zombies can drag you down and kill you. Dependent on zombie strength. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Crawlers Drag Down**<br>`ZombieLore.ZombiesCrawlersDragDown` | boolean; code default `false`; Apocalypse `false` | If crawler zombies beside a player contribute to the chance of being dragged down and killed by a group of zombies. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Zombie Lunge**<br>`ZombieLore.ZombiesFenceLunge` | boolean; code default `true`; Apocalypse `true` | If zombies have a chance to lunge at you after climbing over a fence or through a window if you're too close. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Zombie Armor Factor**<br>`ZombieLore.ZombiesArmorFactor` | double 0.0–100.0; code default `2.0`; Apocalypse `2.0` | Serves as a multiplier when determining the effectiveness of armor worn by zombies. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Maximum Zombie Armor Defense**<br>`ZombieLore.ZombiesMaxDefense` | integer 0–100; code default `85`; Apocalypse `85` | The maximum defense percentage that any worn protective garments can provide to a zombie. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Chance Of Attached Weapon**<br>`ZombieLore.ChanceOfAttachedWeapon` | integer 0–100; code default `6`; Apocalypse `6` | Percentage chance of having a random attached weapon. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Zombie Fall Damage Multiplier**<br>`ZombieLore.ZombiesFallDamage` | double 0.0–100.0; code default `1.0`; Apocalypse `1.0` | How much damage zombies take when falling from height. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Fake Dead Zombie Reanimation**<br>`ZombieLore.DisableFakeDead` | enum 1–3; code default `1`; Apocalypse `1` | Whether some dead-looking zombies will reanimate and attack the player. Values: 1=World Zombies; 2=World and Combat Zombies; 3=Never. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Player Spawn Area**<br>`ZombieLore.PlayerSpawnZombieRemoval` | enum 1–4; code default `1`; Apocalypse `1` | Zombies will not spawn where players spawn. Values: 1=Inside the building and around it; 2=Inside the building; 3=Inside the room; 4=Zombies can spawn anywhere. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Zombies To Damage Fences**<br>`ZombieLore.FenceThumpersRequired` | integer -1–100; code default `50`; Apocalypse `25` | How many zombies it takes to damage a tall fence. | `Zombies`, `ZombieConfig.PopulationMultiplier` |
| **Fence Damage Multiplier**<br>`ZombieLore.FenceDamageMultiplier` | double 0.01f–100.0; code default `1.0`; Apocalypse `1.0` | How quickly zombies damage tall fences. | `Zombies`, `ZombieConfig.PopulationMultiplier` |

### Time and climate

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Day Length (in real time)**<br>`DayLength` | enum 1–27; code default `4`; Apocalypse `4` | Real minutes per full in-game day. It scales most world-time processes together; real-time mode maps one real day to one game day. Values: 1=15 Minutes; 2=30 Minutes; 3=1 Hour; 4=1 Hour, 30 Minutes; 5=2 Hours; 6=3 Hours; 7=4 Hours; 8=5 Hours; 9=6 Hours; 10=7 Hours; 11=8 Hours; 12=9 Hours; 13=10 Hours; 14=11 Hours; 15=12 Hours; 16=13 Hours; 17=14 Hours; 18=15 Hours; 19=16 Hours; 20=17 Hours; 21=18 Hours; 22=19 Hours; 23=20 Hours; 24=21 Hours; 25=22 Hours; 26=23 Hours; 27=Real-time. | Independent/no hard gate identified |
| **Start Year**<br>`StartYear` | enum 1–100; code default `1`; Apocalypse `1` | Offset from the game's base start year used to initialise the calendar; combines with start month/day/time. | `StartMonth`, `StartDay`, `StartTime` |
| **Start Month**<br>`StartMonth` | enum 1–12; code default `7`; Apocalypse `7` | Month in which the game starts. Values: 1=January; 2=February; 3=March; 4=April; 5=May; 6=June; 7=July; 8=August; 9=September; 10=October; 11=November; 12=December. | `StartYear`, `StartDay`, `StartTime` |
| **Start Day**<br>`StartDay` | enum 1–31; code default `23`; Apocalypse `9` | Day of the month in which the games starts. | `StartYear`, `StartMonth`, `StartTime` |
| **Start Hour**<br>`StartTime` | enum 1–9; code default `2`; Apocalypse `2` | Hour of the day in which the game starts. Values: 1=7 AM; 2=9 AM; 3=12 PM; 4=2 PM; 5=5 PM; 6=9 PM; 7=12 AM; 8=2 AM; 9=5 AM. | `StartYear`, `StartMonth`, `StartDay` |
| **Day / Night Cycle**<br>`DayNightCycle` | enum 1–3; code default `1`; Apocalypse `1` | Whether the time of day changes naturally, or it's always day/night. Values: 1=Normal; 2=Endless Day; 3=Endless Night. | Independent/no hard gate identified |
| **Climate Cycle**<br>`ClimateCycle` | enum 1–6; code default `1`; Apocalypse `1` | Whether weather changes or remains at a single state. Values: 1=Normal; 2=No Weather; 3=Endless Rain; 4=Endless Storm; 5=Endless Snow; 6=Endless Blizzard. | Independent/no hard gate identified |
| **Fog Cycle**<br>`FogCycle` | enum 1–3; code default `1`; Apocalypse `1` | Whether fog occurs naturally, never occurs, or is always present. Values: 1=Normal; 2=No Fog; 3=Endless Fog. | Independent/no hard gate identified |
| **Starter Kit**<br>`StarterKit` | boolean; code default `false`; Apocalypse `false` | Spawn with Chips, a Water Bottle, a Small Backpack, a Baseball Bat, and a Hammer. | Independent/no hard gate identified |
| **Months since the Apocalypse**<br>`TimeSinceApo` | enum 1–13; code default `1`; Apocalypse `1` | How long after the end of the world to begin. This will affect starting world erosion and food spoilage. Does not affect the starting date. Values: 1=0; 2=1; 3=2; 4=3; 5=4; 6=5; 7=6; 8=7; 9=8; 10=9; 11=10; 12=11; 13=12. | Independent/no hard gate identified |

### Loot

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Perishable Food**<br>`FoodLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.8` | Any food that can rot or spoil. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Other Literature**<br>`LiteratureLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | All other items that can be read, including books, fliers, and newspapers. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Skill Books**<br>`SkillBookLoot` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Books that provide skill XP multipliers. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Recipe Resources**<br>`RecipeResourceLoot` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Items that teach recipes. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Medical**<br>`MedicalLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Medicine, bandages and first aid tools. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Survival Essentials**<br>`SurvivalGearsLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Fishing Rods, Tents, camping gear etc. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Non-Perishable Food**<br>`CannedFoodLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Canned and dried food, beverages. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Melee Weapons**<br>`WeaponLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Weapons that are not tools in other categories. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Ranged Weapons**<br>`RangedWeaponLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `1.2` | Also includes weapon attachments. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Ammo**<br>`AmmoLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Loose ammo, boxes and magazines. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Mechanics**<br>`MechanicsLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Vehicle parts and the tools needed to install them. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Other**<br>`OtherLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.8` | Everything else. Also affects foraging for all items in Town/Road zones. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Clothing**<br>`ClothingLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | All wearable items that are not containers. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Bags**<br>`ContainerLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Backpacks and other wearable/equippable containers, eg. cases. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Keys**<br>`KeyLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.4` | Keys for buildings/cars, key rings, and locks. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Media**<br>`MediaLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | VHS tapes and CDs. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Mementos**<br>`MementoLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Spiffo items, plushies, and other collectible keepsake items eg. Photos. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Cooking**<br>`CookwareLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Items that are used in cooking, including those (eg. knives) which can be weapons. Does not include food. Includes both usable and unusable items. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Material**<br>`MaterialLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Items and weapons that are used as ingredients for crafting or building. This is a general category that does not include items belonging to other categories such as Cookware or Medical. Does not include Tools. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Farming**<br>`FarmingLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Items and weapons which are used in both animal and plant agriculture, such as Seeds, Trowels, or Shovels. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted`, `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Tools**<br>`ToolLootNew` | double 0.0–4.0; code default `0.6`; Apocalypse `0.6` | Items and weapons which are Tools but don't fit in other categories such as Mechanics or Farming. | `RollsMultiplier`, `MaximumDiminishedLoot`, `MaximumLooted` |
| **Rolls Multiplier [!]**<br>`RollsMultiplier` | double 0.1–100.0; code default `1.0`; Apocalypse `1.0` | Multiplies procedural-distribution roll counts before category rarity and other loot modifiers are applied. | `all category loot multipliers` |
| **Loot Item Removal List**<br>`LootItemRemovalList` | text; code default `""` | Comma-separated full item types removed from generated loot. Story/zombie loot are only included when their separate toggles are enabled. | Independent/no hard gate identified |
| **Remove Unwanted Story Loot**<br>`RemoveStoryLoot` | boolean; code default `false`; Apocalypse `false` | Extends `LootItemRemovalList` filtering to story loot. | Independent/no hard gate identified |
| **Remove Unwanted Zombie Loot**<br>`RemoveZombieLoot` | boolean; code default `false`; Apocalypse `false` | Extends `LootItemRemovalList` filtering to zombie-carried loot. | Independent/no hard gate identified |
| **Zombie Population Loot Effect**<br>`ZombiePopLootEffect` | integer 0–20; code default `10`; Apocalypse `0` | Adds local meta-chunk zombie intensity × this value to an item's base spawn chance. `0` disables the density bonus; this is additive, not a population multiplier or a neutral-at-10 scale. | `ZombieConfig.PopulationMultiplier`, `all category loot multipliers` |
| **Insanely Rare Loot Factor**<br>`InsaneLootFactor` | double 0.0–0.2; code default `0.05`; Apocalypse `0.05` | Numeric multiplier substituted when a legacy/preset loot rarity is Insanely Rare; category values are the newer direct controls. | Independent/no hard gate identified |
| **Extremely Rare Loot Factor**<br>`ExtremeLootFactor` | double 0.05–0.6; code default `0.2`; Apocalypse `0.2` | Numeric multiplier substituted when a legacy/preset loot rarity is Extremely Rare; category values are the newer direct controls. | Independent/no hard gate identified |
| **Rare Loot Factor**<br>`RareLootFactor` | double 0.2–1.0; code default `0.6`; Apocalypse `0.6` | Numeric multiplier substituted when a legacy/preset loot rarity is Rare; category values are the newer direct controls. | Independent/no hard gate identified |
| **Normal Loot Factor**<br>`NormalLootFactor` | double 0.6–2.0; code default `1.0`; Apocalypse `1.0` | Numeric multiplier substituted when a legacy/preset loot rarity is Normal; category values are the newer direct controls. | Independent/no hard gate identified |
| **Common Loot Factor**<br>`CommonLootFactor` | double 1.0–3.0; code default `2.0`; Apocalypse `2.0` | Numeric multiplier substituted when a legacy/preset loot rarity is Common; category values are the newer direct controls. | Independent/no hard gate identified |
| **Abundant Loot Factor**<br>`AbundantLootFactor` | double 2.0–4.0; code default `3.0`; Apocalypse `3.0` | Numeric multiplier substituted when a legacy/preset loot rarity is Abundant; category values are the newer direct controls. | Independent/no hard gate identified |
| **Loot Seen Prevent Hours**<br>`SeenHoursPreventLootRespawn` | integer 0–Integer.MAX_VALUE; code default `0`; Apocalypse `0` | A container/cell seen by a player inside this many hours is ineligible for loot respawn. `0` disables this protection. | `HoursForLootRespawn` |
| **Hours for Loot Respawn**<br>`HoursForLootRespawn` | integer 0–Integer.MAX_VALUE; code default `0`; Apocalypse `0` | Interval in world hours between loot-restock attempts. `0` disables loot respawn, making the other loot-respawn controls inert. | Independent/no hard gate identified |
| **Max Items For Loot Respawn**<br>`MaxItemsForLootRespawn` | integer 0–Integer.MAX_VALUE; code default `5`; Apocalypse `5` | Containers at or above this item count are not topped up during loot respawn. | `HoursForLootRespawn` |
| **Construction Prevents Loot Respawn**<br>`ConstructionPreventsLootRespawn` | boolean; code default `true`; Apocalypse `true` | When enabled, player construction in the area prevents loot respawn there. | `HoursForLootRespawn` |

### Pre-looted and trashed buildings

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Maximum Looted Building Rooms**<br>`MaximumLootedBuildingRooms` | integer 0–200; code default `50`; Apocalypse `50` | Eligibility ceiling, not a partial-room cap. `RBLooted` and `RBTrashed` reject the entire building when `BuildingDef.getRooms().size()` exceeds `MaximumLootedBuildingRooms`; `RBShopLooted` accepts actual shops before its non-shop room-limit check. | `MaximumLooted`, `DaysUntilMaximumLooted` |
| **Maximum Looted Building Chance**<br>`MaximumLooted` | integer 0–200; code default `50`; Apocalypse `25` | Upper value used by `SandboxOptions.getCurrentLootedChance()`. When positive, it ramps using `DaysUntilMaximumLooted`; it drives the Trashed Building story chance and the severity of some looted/trashed stories. Values at or above 100 saturate percentage-style chance checks. | `DaysUntilMaximumLooted`, `RuralLooted`, `MaximumLootedBuildingRooms`, `TimeSinceApo` |
| **Days Until Max Looted Building Chance**<br>`DaysUntilMaximumLooted` | integer 0–3650; code default `90`; Apocalypse `90` | Number of apocalypse days over which `MaximumLooted` ramps to its configured value. `0` returns `MaximumLooted` immediately. | `MaximumLooted`, `RuralLooted`, `TimeSinceApo` |
| **Rural Building Looted Chance Multiplier**<br>`RuralLooted` | double 0.0–2.0; code default `0.5`; Apocalypse `0.5` | Shared rural multiplier used by both `SandboxOptions.getCurrentLootedChance(IsoGridSquare)` and `SandboxOptions.getCurrentDiminishedLootPercentage(IsoGridSquare)`. Build 42.19 casts it to an integer before multiplication. | `MaximumLooted`, `DaysUntilMaximumLooted`, `MaximumDiminishedLoot`, `DaysUntilMaximumDiminishedLoot` |

### Diminished generated loot

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Maximum Diminished Loot Percentage**<br>`MaximumDiminishedLoot` | integer 0–100; code default `0`; Apocalypse `20` | Upper percentage removed from ordinary generated loot by `SandboxOptions.getCurrentLootMultiplier(IsoGridSquare)`. It does not mark a building as pre-looted. | `DaysUntilMaximumDiminishedLoot`, `RuralLooted`, `TimeSinceApo` |
| **Days Until Maximum Diminished Loot**<br>`DaysUntilMaximumDiminishedLoot` | integer 0–3650; code default `3650`; Apocalypse `3650` | Number of apocalypse days over which `MaximumDiminishedLoot` ramps to its configured percentage. `0` applies `MaximumDiminishedLoot` immediately. | `MaximumDiminishedLoot`, `RuralLooted`, `TimeSinceApo` |

### Utilities

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Water Shutoff**<br>`WaterShut` | enum 1–9; code default `2`; Apocalypse `2` | How long after the default start date (July 9, 1993) that plumbing fixtures (eg. sinks) stop being infinite sources of water. Values: 1=Instant; 2=0 - 30 Days; 3=0 - 2 Months; 4=0 - 6 Months; 5=0 - 1 Year; 6=0 - 5 Years; 7=2 - 6 Months; 8=6 - 12 Months; 9=Disabled. | `WaterShutModifier` |
| **Electricity Shutoff**<br>`ElecShut` | enum 1–9; code default `2`; Apocalypse `2` | How long after the default start date (July 9, 1993) that the world's electricity turns off for good. Values: 1=Instant; 2=14 - 30 Days; 3=14 Days - 2 Months; 4=14 Days - 6 Months; 5=14 Days - 1 Year; 6=14 Days - 5 Years; 7=2 - 6 Months; 8=6 - 12 Months; 9=Disabled. | `ElecShutModifier` |
| **Alarm Battery Decay**<br>`AlarmDecay` | enum 1–6; code default `2`; Apocalypse `2` | How long alarm batteries can last for after the power shuts off. Values: 1=Instant; 2=0 - 30 Days; 3=0 - 2 Months; 4=0 - 6 Months; 5=0 - 1 Year; 6=0 - 5 Years. | `AlarmDecayModifier` |
| **Water Shutoff**<br>`WaterShutModifier` | integer -1–Integer.MAX_VALUE; code default `14`; Apocalypse `14` | Exact world-age day at which water shuts off; `-1` lets the corresponding enum choose/randomise it. | `WaterShut` |
| **Electricity Shutoff**<br>`ElecShutModifier` | integer -1–Integer.MAX_VALUE; code default `14`; Apocalypse `14` | Exact world-age day at which electricity shuts off; `-1` lets the corresponding enum choose/randomise it. | `ElecShut` |
| **Alarm Battery Decay**<br>`AlarmDecayModifier` | integer -1–Integer.MAX_VALUE; code default `14`; Apocalypse `14` | Exact world-age day at which alarms stop being available; `-1` lets the corresponding enum choose/randomise it. | `AlarmDecay` |
| **Generator Fuel Consumption**<br>`GeneratorFuelConsumption` | double 0.0–100.0; code default `0.1`; Apocalypse `0.1` | Fuel consumed per in-game hour. Generator runtime also depends on electrical load and generator state. | Independent/no hard gate identified |
| **Generators**<br>`GeneratorSpawning` | enum 1–7; code default `5`; Apocalypse `4` | The chance of electrical generators spawning on the map. Values: 1=None (not recommended); 2=Insanely Rare; 3=Extremely Rare; 4=Rare; 5=Normal; 6=Common; 7=Abundant. | Independent/no hard gate identified |
| **Generator Working in Exterior**<br>`AllowExteriorGenerator` | boolean; code default `true`; Apocalypse `true` | If enabled, generators will work on exterior tiles. This will allow, for example, the powering of gas pumps. | Independent/no hard gate identified |
| **Light Bulb Lifespan**<br>`LightBulbLifespan` | double 0.0–1000.0; code default `1.0`; Apocalypse `2.0` | The higher the value, the longer lightbulbs last before breaking. If 0, lightbulbs will never break. Does not affect vehicle headlights. | Independent/no hard gate identified |
| **Generator tile range**<br>`GeneratorTileRange` | integer 1–100; code default `20`; Apocalypse `20` | Horizontal tile radius in which a generator supplies power. | `GeneratorVerticalPowerRange`, `GeneratorFuelConsumption` |
| **Generator vertical range**<br>`GeneratorVerticalPowerRange` | integer 1–15; code default `3`; Apocalypse `3` | Maximum vertical floor distance supplied by a generator. | `GeneratorTileRange`, `GeneratorFuelConsumption` |

### World generation and stories

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **House Alarms Frequency**<br>`Alarm` | enum 1–6; code default `4`; Apocalypse `4` | How likely the player is to activate a house alarm when breaking into a new house. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | Independent/no hard gate identified |
| **Locked Houses Frequency**<br>`LockedHouses` | enum 1–6; code default `4`; Apocalypse `6` | How frequently the doors of homes and buildings will be locked when discovered. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | Independent/no hard gate identified |
| **Helicopter**<br>`Helicopter` | enum 1–4; code default `2`; Apocalypse `2` | How regularly a helicopter passes over the Event Zone. Values: 1=Never; 2=Once; 3=Sometimes; 4=Often. | Independent/no hard gate identified |
| **Meta Event**<br>`MetaEvent` | enum 1–3; code default `2`; Apocalypse `2` | How often zombie-attracting metagame events like distant gunshots will occur. Values: 1=Never; 2=Sometimes; 3=Often. | Independent/no hard gate identified |
| **Sleeping Event**<br>`SleepingEvent` | enum 1–3; code default `1`; Apocalypse `1` | How often events during the player's sleep, like nightmares, occur. Values: 1=Never; 2=Sometimes; 3=Often. | Independent/no hard gate identified |
| **Randomized Zone Stories Chance**<br>`ZoneStoryChance` | enum 1–7; code default `3`; Apocalypse `3` | The chance of stories specific to map zones (eg. a campsite in a forest) spawning. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always Tries. | Independent/no hard gate identified |
| **Basement Spawn Frequency**<br>`Basement.SpawnFrequency` | enum 1–7; code default `4`; Apocalypse `4` | How frequently basements spawn at random locations. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always. | Independent/no hard gate identified |

### Vehicles

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Randomized Road Stories Chance**<br>`VehicleStoryChance` | enum 1–7; code default `3`; Apocalypse `3` | The chance of road stories (eg. police roadblocks) spawning. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always Tries. | Independent/no hard gate identified |
| **Vehicles**<br>`EnableVehicles` | boolean; code default `true`; Apocalypse `true` | If vehicles will spawn. | Independent/no hard gate identified |
| **Vehicle Spawn Rate**<br>`CarSpawnRate` | enum 1–5; code default `4`; Apocalypse `3` | How frequently vehicles can be discovered on the map. Values: 1=None; 2=Very Low; 3=Low; 4=Normal; 5=High. | Independent/no hard gate identified |
| **Easy Use**<br>`VehicleEasyUse` | boolean; code default `false`; Apocalypse `false` | Whether found vehicles are locked, need keys to start etc. | Independent/no hard gate identified |
| **Initial Gas**<br>`InitialGas` | enum 1–6; code default `3`; Apocalypse `2` | How full the gas tank of discovered vehicles will be. Values: 1=Very Low; 2=Low; 3=Normal; 4=High; 5=Very High; 6=Full. | Independent/no hard gate identified |
| **Infinite Gas Pumps**<br>`FuelStationGasInfinite` | boolean; code default `false`; Apocalypse `false` | Makes fuel pumps inexhaustible; when true, min/max/empty-chance initial reserves are irrelevant. | Independent/no hard gate identified |
| **Initial Minimum Gas Pump Amount**<br>`FuelStationGasMin` | double 0.0–1.0; code default `0.0`; Apocalypse `0.0` | Lower bound for finite fuel-station starting reserves. | `FuelStationGasInfinite` |
| **Initial Maximum Gas Pump Amount**<br>`FuelStationGasMax` | double 0.0–1.0; code default `0.7`; Apocalypse `0.8` | Upper bound for finite fuel-station starting reserves. | `FuelStationGasInfinite` |
| **Initial Gas Pump Empty Chance**<br>`FuelStationGasEmptyChance` | integer 0–100; code default `20`; Apocalypse `20` | Percentage chance a finite fuel station starts empty. | `FuelStationGasInfinite` |
| **Locked Vehicle Frequency**<br>`LockedCar` | enum 1–6; code default `4`; Apocalypse `4` | How likely cars will be locked Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | Independent/no hard gate identified |
| **Gas Consumption**<br>`CarGasConsumption` | double 0.0–100.0; code default `1.0`; Apocalypse `1.0` | How gas-hungry vehicles are. | Independent/no hard gate identified |
| **General Condition**<br>`CarGeneralCondition` | enum 1–5; code default `3`; Apocalypse `3` | General condition discovered vehicles will be in. Values: 1=Very Low; 2=Low; 3=Normal; 4=High; 5=Very High. | Independent/no hard gate identified |
| **Car Damage on Impact**<br>`CarDamageOnImpact` | enum 1–5; code default `3`; Apocalypse `3` | The amount of damage dealt to vehicles that crash. Values: 1=Very Low; 2=Low; 3=Normal; 4=High; 5=Very High. | Independent/no hard gate identified |
| **Player Damage From Vehicle Impact**<br>`DamageToPlayerFromHitByACar` | enum 1–5; code default `1`; Apocalypse `1` | Damage received by the player from being crashed into. Values: 1=None; 2=Low; 3=Normal; 4=High; 5=Very High. | Independent/no hard gate identified |
| **Car Wreck Congestion**<br>`TrafficJam` | boolean; code default `true`; Apocalypse `true` | If traffic jams consisting of wrecked cars will appear on main roads. | Independent/no hard gate identified |
| **Vehicle Alarms Frequency**<br>`CarAlarm` | enum 1–6; code default `4`; Apocalypse `3` | How frequently discovered vehicles have active alarms. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | Independent/no hard gate identified |
| **Siren Shutoff Hours**<br>`SirenShutoffHours` | double 0.0–168.0; code default `0.0`; Apocalypse `0.0` | How many in-game hours before a wailing siren shuts off. | Independent/no hard gate identified |
| **Chance Has Gas**<br>`ChanceHasGas` | enum 1–3; code default `2`; Apocalypse `2` | The chance of finding a vehicle with gas in its tank. Values: 1=Low; 2=Normal; 3=High. | Independent/no hard gate identified |
| **Recent Survivor Vehicles**<br>`RecentlySurvivorVehicles` | enum 1–4; code default `3`; Apocalypse `2` | Whether a player can discover a car that has been cared for after the Knox infection struck. Values: 1=None; 2=Low; 3=Normal; 4=High. | Independent/no hard gate identified |
| **Vehicle Sirens Attract Zombies**<br>`SirenEffectsZombies` | boolean; code default `true`; Apocalypse `true` | If zombies will head towards the sound of vehicle sirens. | Independent/no hard gate identified |

### Animals

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Stats Reduction Speed**<br>`AnimalStatsModifier` | enum 1–6; code default `4`; Apocalypse `4` | Speed at which animals stats (hunger, thirst etc.) reduce. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Meta Stats Reduction Speed**<br>`AnimalMetaStatsModifier` | enum 1–6; code default `4`; Apocalypse `4` | Speed at which animals stats (hunger, thirst etc.) reduce while in meta. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Pregnancy Time**<br>`AnimalPregnancyTime` | enum 1–6; code default `2`; Apocalypse `4` | How long animals will be pregnant for before giving birth. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Aging Modifier Speed**<br>`AnimalAgeModifier` | enum 1–6; code default `3`; Apocalypse `4` | Speed at which animals age. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Milk Increase Speed**<br>`AnimalMilkIncModifier` | enum 1–6; code default `3`; Apocalypse `4` | Multiplier band for milk regeneration over world time; only milk-producing animals use it. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Wool Increase Speed**<br>`AnimalWoolIncModifier` | enum 1–6; code default `3`; Apocalypse `4` | Multiplier band for wool growth over world time; only wool-producing animals use it. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Animal Spawn Chance**<br>`AnimalRanchChance` | enum 1–7; code default `7`; Apocalypse `5` | The chance of finding animals in farm. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always. | `TimeSinceApo` |
| **Grass Regrowth time**<br>`AnimalGrassRegrowTime` | integer 1–9999; code default `240`; Apocalypse `240` | The number of hours grass will regrow after being eaten by an animal or cut by the player. | `AnimalRanchChance`, `TimeSinceApo` |
| **Meta Predator**<br>`AnimalMetaPredator` | boolean; code default `false`; Apocalypse `false` | If a meta (ie. not actually visible in-game) fox may attack your chickens if the hutch's door is left open at night. | `AnimalRanchChance`, `TimeSinceApo` |
| **Breeding Season**<br>`AnimalMatingSeason` | boolean; code default `true`; Apocalypse `true` | If on, animals will only mate during their breeding season (if any). Otherwise they can reproduce/lay eggs all year round. | `AnimalRanchChance`, `TimeSinceApo` |
| **Egg Hatch Time**<br>`AnimalEggHatch` | enum 1–6; code default `3`; Apocalypse `4` | How long before baby animals will hatch from eggs. Values: 1=Ultra Fast; 2=Very Fast; 3=Fast; 4=Normal; 5=Slow; 6=Very Slow. | `AnimalRanchChance`, `TimeSinceApo` |
| **Animals Attract Zombies**<br>`AnimalSoundAttractZombies` | boolean; code default `false`; Apocalypse `true` | If true, animal calls will attract nearby zombies. | `AnimalRanchChance`, `TimeSinceApo` |
| **Animal Tracks Chance**<br>`AnimalTrackChance` | enum 1–6; code default `4`; Apocalypse `4` | The chance of animals leaving tracks. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | `AnimalRanchChance`, `TimeSinceApo` |
| **Animal Paths Chance**<br>`AnimalPathChance` | enum 1–6; code default `4`; Apocalypse `4` | The chance of creating a path for animals to be hunted. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | `AnimalRanchChance`, `TimeSinceApo` |
| **Maximum Vermin Index**<br>`MaximumRatIndex` | integer 0–50; code default `25`; Apocalypse `25` | The frequency and intensity of eg. rats in infested buildings. | Independent/no hard gate identified |
| **Days Until Maximum Vermin Index**<br>`DaysUntilMaximumRatIndex` | integer 0–365; code default `90`; Apocalypse `90` | How long it takes for the Maximum Vermin Index to be reached. | Independent/no hard gate identified |

### Farming and resources

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Farming Speed**<br>`Farming` | enum 1–5; code default `3`; Apocalypse `3` | Legacy farming-speed enum retained for preset compatibility; `FarmingSpeedNew` is the precise multiplier used by current farming code. Values: 1=Very Fast; 2=Fast; 3=Normal; 4=Slow; 5=Very Slow. | `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Compost Time**<br>`CompostTime` | enum 1–8; code default `2`; Apocalypse `2` | How long it takes for food to break down in a composter. Values: 1=1 Week; 2=2 Weeks; 3=3 Weeks; 4=4 Weeks; 5=6 Weeks; 6=8 Weeks; 7=10 Weeks; 8=12 Weeks. | Independent/no hard gate identified |
| **Plant Resilience**<br>`PlantResilience` | enum 1–5; code default `3`; Apocalypse `3` | How much water plants will lose per day, and their ability to avoid disease. Values: 1=Very High; 2=High; 3=Normal; 4=Low; 5=Very Low. | `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Farming's Abundance**<br>`PlantAbundance` | enum 1–5; code default `3`; Apocalypse `3` | Legacy crop-yield enum retained for compatibility; `FarmingAmountNew` is the precise current multiplier. Values: 1=Very Poor; 2=Poor; 3=Normal; 4=Abundant; 5=Very Abundant. | `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Kill Crops Grown Inside**<br>`KillInsideCrops` | boolean; code default `true`; Apocalypse `true` | When enabled, crops and herbs grown inside buildings will die. Does not affect houseplants. | `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Plant Growing Seasons**<br>`PlantGrowingSeasons` | boolean; code default `true`; Apocalypse `true` | When enabled, the growth of plants is affected by seasons. | `FarmingSpeedNew`, `FarmingAmountNew` |
| **Farming Speed**<br>`FarmingSpeedNew` | double 0.1–100.0; code default `1.0`; Apocalypse `1.0` | The speed of plant growth. | `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Farming Abundance**<br>`FarmingAmountNew` | double 0.1–10.0; code default `1.0`; Apocalypse `1.0` | The abundance of harvested crops. | `FarmingSpeedNew`, `PlantGrowingSeasons` |
| **Clay chance - Lake**<br>`ClayLakeChance` | double 0.0–1.0; code default `0.05`; Apocalypse `0.05` | Chance to turn a dirt floor into a clay floor. Applies to lakes. | Independent/no hard gate identified |
| **Clay chance - River**<br>`ClayRiverChance` | double 0.0–1.0; code default `0.05`; Apocalypse `0.05` | Chance to turn a dirt floor into a clay floor. Applies to rivers. | Independent/no hard gate identified |

### Nature, fishing and foraging

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Nature's Abundance**<br>`NatureAbundance` | enum 1–5; code default `3`; Apocalypse `3` | The abundance of items found in Foraging mode. Values: 1=Very Poor; 2=Poor; 3=Normal; 4=Abundant; 5=Very Abundant. | Independent/no hard gate identified |
| **Corpse Maggot Spawn**<br>`MaggotSpawn` | enum 1–3; code default `1`; Apocalypse `1` | If/when maggots can spawn in corpses. Values: 1=In and Around Bodies; 2=In Bodies Only; 3=Never. | Independent/no hard gate identified |
| **Fishing Abundance**<br>`FishAbundance` | enum 1–5; code default `3`; Apocalypse `2` | The abundance of fish in rivers and lakes. Values: 1=Very Poor; 2=Poor; 3=Normal; 4=Abundant; 5=Very Abundant. | Independent/no hard gate identified |

### Player health

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Stats Decrease**<br>`StatsDecrease` | enum 1–5; code default `3`; Apocalypse `3` | How fast the player's hunger, thirst, and fatigue will decrease. Values: 1=Very Fast; 2=Fast; 3=Normal; 4=Slow; 5=Very Slow. | Independent/no hard gate identified |
| **Nutrition System**<br>`Nutrition` | boolean; code default `false`; Apocalypse `true` | Nutritional value of food affects the player's condition. Turning this off will stop the player gaining or losing weight. | Independent/no hard gate identified |
| **Endurance Regeneration**<br>`EndRegen` | enum 1–5; code default `3`; Apocalypse `3` | Recovery from being tired after performing actions. Values: 1=Very Fast; 2=Fast; 3=Normal; 4=Slow; 5=Very Slow. | Independent/no hard gate identified |
| **Bone Fracture**<br>`BoneFracture` | boolean; code default `true`; Apocalypse `true` | If survivors can get broken limbs from impacts, zombie damage, falls etc. | Independent/no hard gate identified |
| **Injury Severity**<br>`InjurySeverity` | enum 1–3; code default `2`; Apocalypse `2` | The impact that injuries have on your body, and their healing time. Values: 1=Low; 2=Normal; 3=High. | Independent/no hard gate identified |
| **Enable Poisoning**<br>`EnablePoisoning` | enum 1–3; code default `1`; Apocalypse `1` | If poison can be added to food. Values: 1=True; 2=False; 3=Only bleach poisoning is disabled. | Independent/no hard gate identified |
| **Muscle Strain Factor**<br>`MuscleStrainFactor` | double 0.0–10.0; code default `1.0`; Apocalypse `0.7` | Functions as a multiplier when applying muscle strain from swinging weapons or carrying heavy loads. | Independent/no hard gate identified |
| **Discomfort Factor**<br>`DiscomfortFactor` | double 0.0–10.0; code default `1.0`; Apocalypse `0.8` | Functions as a multiplier when applying discomfort from worn items. | Independent/no hard gate identified |
| **Wound Infection Damage Factor**<br>`WoundInfectionFactor` | double 0.0–10.0; code default `0.0`; Apocalypse `1.0` | If greater than zero damage can be taken from serious wound infections. | Independent/no hard gate identified |

### Character, skills and literature

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Media List Meta Knowledge**<br>`MetaKnowledge` | enum 1–3; code default `3`; Apocalypse `3` | If a piece of media hasn't been fully seen or read, this setting determines whether it's displayed fully, displayed as "???", or hidden completely. Values: 1=Fully revealed; 2=Shown as ???; 3=Completely hidden. | Independent/no hard gate identified |
| **See Not Known Recipes**<br>`SeeNotLearntRecipe` | boolean; code default `true`; Apocalypse `true` | If true, you will be able to see any recipes that can be done with a station, even if you haven't learnt them yet. | Independent/no hard gate identified |
| **Maximum Media XP Level**<br>`LevelForMediaXPCutoff` | integer 0–10; code default `3`; Apocalypse `3` | When a skill is at this level or above, television/VHS/other media will not provide XP for it. | Independent/no hard gate identified |
| **Maximum Dismantling XP Level**<br>`LevelForDismantleXPCutoff` | integer 0–10; code default `0`; Apocalypse `0` | When a skill is at this level or above, scrapping furniture does not provide XP for the relevant skill. Does not apply to Electrical. | Independent/no hard gate identified |
| **Literature Cooldown Days**<br>`LiteratureCooldown` | integer 1–365; code default `90`; Apocalypse `45` | Number of days before one can benefit from reading previously read literature items. | Independent/no hard gate identified |
| **Negative Traits Penalty**<br>`NegativeTraitsPenalty` | enum 1–4; code default `1`; Apocalypse `1` | If there are diminishing returns on bonus trait points provided from selecting multiple negative traits. Values: 1=None; 2=1 point penalty for every 3 negative traits selected; 3=1 point penalty for every 2 negative traits selected; 4=1 point penalty for every negative trait selected after the first. | Independent/no hard gate identified |
| **Minutes Per Skill Book Page**<br>`MinutesPerPage` | double 0.0–60.0; code default `2.0`; Apocalypse `2.0` | The number of in-game minutes it takes to read one page of a skill book. | Independent/no hard gate identified |

### XP multipliers

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Global Multiplier**<br>`MultiplierConfig.Global` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Global XP multiplier applied when `MultiplierConfig.GlobalToggle` is enabled. | `XPmultiplier`, `XPBoost` |
| **Use Global Multiplier**<br>`MultiplierConfig.GlobalToggle` | boolean; code default `true`; Apocalypse `true` | Chooses global-only XP scaling versus the individual per-skill `MultiplierConfig.*` values. | `XPmultiplier`, `XPBoost` |
| **Fitness Multiplier**<br>`MultiplierConfig.Fitness` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Fitness skill levels up. | `XPmultiplier`, `XPBoost` |
| **Strength Multiplier**<br>`MultiplierConfig.Strength` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Strength skill levels up. | `XPmultiplier`, `XPBoost` |
| **Sprinting Multiplier**<br>`MultiplierConfig.Sprinting` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Sprinting skill levels up. | `XPmultiplier`, `XPBoost` |
| **Lightfooted Multiplier**<br>`MultiplierConfig.Lightfoot` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Lightfooted skill levels up. | `XPmultiplier`, `XPBoost` |
| **Nimble Multiplier**<br>`MultiplierConfig.Nimble` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Nimble skill levels up. | `XPmultiplier`, `XPBoost` |
| **Sneaking Multiplier**<br>`MultiplierConfig.Sneak` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Sneaking skill levels up. | `XPmultiplier`, `XPBoost` |
| **Axe Multiplier**<br>`MultiplierConfig.Axe` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Axe skill levels up. | `XPmultiplier`, `XPBoost` |
| **Long Blunt Multiplier**<br>`MultiplierConfig.Blunt` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Long Blunt skill levels up. | `XPmultiplier`, `XPBoost` |
| **Short Blunt Multiplier**<br>`MultiplierConfig.SmallBlunt` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Short Blunt skill levels up. | `XPmultiplier`, `XPBoost` |
| **Long Blade Multiplier**<br>`MultiplierConfig.LongBlade` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Long Blade skill levels up. | `XPmultiplier`, `XPBoost` |
| **Short Blade Multiplier**<br>`MultiplierConfig.SmallBlade` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Short Blade skill levels up. | `XPmultiplier`, `XPBoost` |
| **Spear Multiplier**<br>`MultiplierConfig.Spear` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Spear skill levels up. | `XPmultiplier`, `XPBoost` |
| **Maintenance Multiplier**<br>`MultiplierConfig.Maintenance` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Maintenance skill levels up. | `XPmultiplier`, `XPBoost` |
| **Carpentry Multiplier**<br>`MultiplierConfig.Woodwork` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Carpentry skill levels up. | `XPmultiplier`, `XPBoost` |
| **Cooking Multiplier**<br>`MultiplierConfig.Cooking` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Cooking skill levels up. | `XPmultiplier`, `XPBoost` |
| **Agriculture Multiplier**<br>`MultiplierConfig.Farming` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Legacy farming-speed enum retained for preset compatibility; `FarmingSpeedNew` is the precise multiplier used by current farming code. | `XPmultiplier`, `XPBoost`, `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **First Aid Multiplier**<br>`MultiplierConfig.Doctor` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which First Aid skill levels up. | `XPmultiplier`, `XPBoost` |
| **Electrical Multiplier**<br>`MultiplierConfig.Electricity` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Electrical skill levels up. | `XPmultiplier`, `XPBoost` |
| **Welding Multiplier**<br>`MultiplierConfig.MetalWelding` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Welding skill levels up. | `XPmultiplier`, `XPBoost` |
| **Mechanics Multiplier**<br>`MultiplierConfig.Mechanics` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Mechanics skill levels up. | `XPmultiplier`, `XPBoost` |
| **Tailoring Multiplier**<br>`MultiplierConfig.Tailoring` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Tailoring skill levels up. | `XPmultiplier`, `XPBoost` |
| **Aiming Multiplier**<br>`MultiplierConfig.Aiming` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Aiming skill levels up. | `XPmultiplier`, `XPBoost` |
| **Reloading Multiplier**<br>`MultiplierConfig.Reloading` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Reloading skill levels up. | `XPmultiplier`, `XPBoost` |
| **Fishing Multiplier**<br>`MultiplierConfig.Fishing` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Fishing skill levels up. | `XPmultiplier`, `XPBoost` |
| **Trapping Multiplier**<br>`MultiplierConfig.Trapping` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Trapping skill levels up. | `XPmultiplier`, `XPBoost` |
| **Foraging Multiplier**<br>`MultiplierConfig.PlantScavenging` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Foraging skill levels up. | `XPmultiplier`, `XPBoost`, `FarmingSpeedNew`, `FarmingAmountNew`, `PlantGrowingSeasons` |
| **Knapping Multiplier**<br>`MultiplierConfig.FlintKnapping` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Knapping skill levels up. | `XPmultiplier`, `XPBoost` |
| **Masonry Multiplier**<br>`MultiplierConfig.Masonry` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Masonry skill levels up. | `XPmultiplier`, `XPBoost` |
| **Pottery Multiplier**<br>`MultiplierConfig.Pottery` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Pottery skill levels up. | `XPmultiplier`, `XPBoost` |
| **Carving Multiplier**<br>`MultiplierConfig.Carving` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Carving skill levels up. | `XPmultiplier`, `XPBoost` |
| **Animal Care Multiplier**<br>`MultiplierConfig.Husbandry` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Animal Care skill levels up. | `XPmultiplier`, `XPBoost` |
| **Tracking Multiplier**<br>`MultiplierConfig.Tracking` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Tracking skill levels up. | `XPmultiplier`, `XPBoost` |
| **Blacksmithing Multiplier**<br>`MultiplierConfig.Blacksmith` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Blacksmithing skill levels up. | `XPmultiplier`, `XPBoost` |
| **Butchering Multiplier**<br>`MultiplierConfig.Butchering` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Butchering skill levels up. | `XPmultiplier`, `XPBoost` |
| **Glassmaking Multiplier**<br>`MultiplierConfig.Glassmaking` | double 0.0–1000.0; code default `1.0`; Apocalypse `1.0` | Rate at which Glassmaking skill levels up. | `XPmultiplier`, `XPBoost` |

### Map

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Allow Mini-Map**<br>`Map.AllowMiniMap` | boolean; code default `false`; Apocalypse `false` | If enabled, a mini-map window will be available. | `Map.AllowWorldMap` |
| **Allow World Map**<br>`Map.AllowWorldMap` | boolean; code default `true`; Apocalypse `true` | If enabled, the world map can be accessed. | `Map.AllowMiniMap` |
| **All Known On Start**<br>`Map.MapAllKnown` | boolean; code default `false`; Apocalypse `false` | Reveals the entire world map; only useful when the world map is allowed. | `Map.AllowWorldMap`, `Map.AllowMiniMap` |
| **Light Needed To Read Map**<br>`Map.MapNeedsLight` | boolean; code default `true`; Apocalypse `true` | Requires light to read map UI; only relevant when a map UI is allowed. | `Map.AllowWorldMap`, `Map.AllowMiniMap` |

### Cleanup, fire and corpses

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **World Item Removal List**<br>`WorldItemRemovalList` | text; code default `"Base.Hat`; Apocalypse `"Base.Hat, Base.Glasses, Base.Maggots, Base.Slug, Base.Slug2, Base.Snail, Base.Worm, Base.Dung_Mouse, Base.Dung_Rat"` | Comma-separated full item types considered by world-item cleanup; blacklist/whitelist meaning is controlled by `ItemRemovalListBlacklistToggle`. | Independent/no hard gate identified |
| **Hours for Removal List**<br>`HoursForWorldItemRemoval` | double 0.0–2.147483647E9; code default `24.0`; Apocalypse `24.0` | Minimum age in world hours before eligible dropped world items are removed. | Independent/no hard gate identified |
| **Time Before Corpse Removal**<br>`HoursForCorpseRemoval` | double -1.0–2.147483647E9; code default `-1.0`; Apocalypse `216.0` | How long, in hours, before dead zombie bodies disappear from the world. If 0, maggots will not spawn on corpses. | Independent/no hard gate identified |
| **Decaying Corpse Health Impact**<br>`DecayingCorpseHealthImpact` | enum 1–5; code default `3`; Apocalypse `3` | The impact that nearby decaying bodies has on the player's health and emotions. Values: 1=None; 2=Low; 3=Normal; 4=High; 5=Insane. | Independent/no hard gate identified |
| **Blood Level**<br>`BloodLevel` | enum 1–5; code default `3`; Apocalypse `3` | How much blood is sprayed on floors and walls by injuries. Values: 1=None; 2=Low; 3=Normal; 4=High; 5=Ultra Gore. | Independent/no hard gate identified |
| **Fire Spread**<br>`FireSpread` | boolean; code default `true`; Apocalypse `true` | If fires spread when started. | Independent/no hard gate identified |
| **Rotten Food Removal**<br>`DaysForRottenFoodRemoval` | integer -1–Integer.MAX_VALUE; code default `-1`; Apocalypse `-1` | Number of in-game days before rotten food is removed from the map. -1 means rotten food is never removed. | Independent/no hard gate identified |
| **Blood Splat Lifespan Days**<br>`BloodSplatLifespanDays` | integer 0–365; code default `0`; Apocalypse `0` | Number of days before old blood splats are removed. Removal happens when map chunks are loaded. 0 means they will never disappear. | Independent/no hard gate identified |
| **Maximum Fire Fuel Hours**<br>`MaximumFireFuelHours` | integer 1–168; code default `8`; Apocalypse `8` | The maximum hours of fuel that can be placed in a campfire, wood stove etc. | Independent/no hard gate identified |
| **Firearms Use Damage Chance**<br>`FirearmUseDamageChance` | enum 1–3; code default `2`; Apocalypse `2` | Replaces Chance-To-Hit mechanics with Chance-To-Damage calculations. This mode prioritizes player aiming. Values: 1=Disabled; 2=Zombies only; 3=All types of target. | Independent/no hard gate identified |
| **Firearm Noise Multiplier**<br>`FirearmNoiseMultiplier` | double 0.2–2.0; code default `1.0`; Apocalypse `1.0` | A multiplier for the distance at which zombies can hear gunshots. | Independent/no hard gate identified |
| **Firearm Jam Multiplier**<br>`FirearmJamMultiplier` | double 0.0–10.0; code default `0.0`; Apocalypse `1.0` | Multiplier for firearm jamming chance. 0 disables jamming. | Independent/no hard gate identified |
| **Firearm Moodle Multiplier**<br>`FirearmMoodleMultiplier` | double 0.0–10.0; code default `1.0`; Apocalypse `1.0` | Multiplier for Moodle effects on hit chance. 0 disables Moodle penalty. | Independent/no hard gate identified |
| **Firearm Weather Multiplier**<br>`FirearmWeatherMultiplier` | double 0.0–10.0; code default `1.0`; Apocalypse `1.0` | Multiplier for the effects of weather (wind, rain and fog) on hit chance. 0 disables weather effect. | Independent/no hard gate identified |
| **Firearm Headgear Effect**<br>`FirearmHeadGearEffect` | boolean; code default `true`; Apocalypse `true` | Enable to have headgear like welding masks affect hit chance | Independent/no hard gate identified |

### Gameplay and miscellaneous

| UI name / raw ID | Type, range and default | Code effect | Related / gated by |
|---|---|---|---|
| **Temperature**<br>`Temperature` | enum 1–5; code default `3`; Apocalypse `3` | The global temperature. Values: 1=Very Cold; 2=Cold; 3=Normal; 4=Hot; 5=Very Hot. | Independent/no hard gate identified |
| **Rain**<br>`Rain` | enum 1–5; code default `3`; Apocalypse `3` | How often it rains. Values: 1=Very Dry; 2=Dry; 3=Normal; 4=Rainy; 5=Very Rainy. | Independent/no hard gate identified |
| **Erosion Speed**<br>`ErosionSpeed` | enum 1–5; code default `3`; Apocalypse `4` | Number of days until the erosion system (which adds vines, long grass, new trees etc. to the world) will reach 100% growth. Values: 1=Very Fast (20 Days); 2=Fast (50 Days); 3=Normal (100 Days); 4=Slow (200 Days); 5=Very Slow (500 Days). | Independent/no hard gate identified |
| **Erosion Days**<br>`ErosionDays` | integer -1–36500; code default `0`; Apocalypse `0` | For a custom Erosion Speed. Zero means use the Erosion Speed option. Maximum is 36,500 days (approximately 100 years). | Independent/no hard gate identified |
| **Food Spoilage**<br>`FoodRotSpeed` | enum 1–5; code default `3`; Apocalypse `3` | How fast that food will spoil, inside or outside of a fridge. Values: 1=Very Fast; 2=Fast; 3=Normal; 4=Slow; 5=Very Slow. | Independent/no hard gate identified |
| **Refrigeration Effectiveness**<br>`FridgeFactor` | enum 1–6; code default `3`; Apocalypse `3` | How effective a fridge will be at keeping food fresh for longer. Values: 1=Very Low; 2=Low; 3=Normal; 4=High; 5=Very High; 6=No decay. | Independent/no hard gate identified |
| **Removal List as Whitelist**<br>`ItemRemovalListBlacklistToggle` | boolean; code default `false`; Apocalypse `false` | Switches world-item cleanup between removing listed types and preserving listed types/removing the rest. | Independent/no hard gate identified |
| **Annotated Map Chance**<br>`AnnotatedMapChance` | enum 1–6; code default `4`; Apocalypse `4` | How often a looted map will have notes on it, written by a deceased survivor. Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often. | Independent/no hard gate identified |
| **Free Trait Points**<br>`CharacterFreePoints` | integer -100–100; code default `0`; Apocalypse `0` | Adds free points during character creation. | Independent/no hard gate identified |
| **Player-built Construction Strength**<br>`ConstructionBonusPoints` | enum 1–5; code default `3`; Apocalypse `3` | Gives player-built constructions extra hit points so they are more resistant to zombie damage. Values: 1=Very Low; 2=Low; 3=Normal; 4=High; 5=Very High. | Independent/no hard gate identified |
| **Darkness during night**<br>`NightDarkness` | enum 1–4; code default `3`; Apocalypse `3` | The level of ambient lighting at night. Values: 1=Pitch Black; 2=Dark; 3=Normal; 4=Bright. | Independent/no hard gate identified |
| **Length of nights**<br>`NightLength` | enum 1–5; code default `3`; Apocalypse `3` | The time from dusk to dawn. Values: 1=Always Night; 2=Long; 3=Normal; 4=Short; 5=Always Day. | Independent/no hard gate identified |
| **Zombie Health Impact**<br>`ZombieHealthImpact` | boolean; code default `false`; Apocalypse `false` | Whether nearby "living" zombies have the same impact on the player's health and emotions. | Independent/no hard gate identified |
| **Clothing Degradation**<br>`ClothingDegradation` | enum 1–4; code default `3`; Apocalypse `3` | How quickly clothing degrades, becomes dirty, and bloodied. Values: 1=Disabled; 2=Slow; 3=Normal; 4=Fast. | Independent/no hard gate identified |
| **Maximum Fog Intensity**<br>`MaxFogIntensity` | enum 1–4; code default `1`; Apocalypse `1` | Maximum intensity of fog. Values: 1=Normal; 2=Moderate; 3=Low; 4=None. | Independent/no hard gate identified |
| **Maximum Rain FX Intensity**<br>`MaxRainFxIntensity` | enum 1–3; code default `1`; Apocalypse `1` | Maximum intensity of rain. Values: 1=Normal; 2=Moderate; 3=Low. | Independent/no hard gate identified |
| **Snow on Ground**<br>`EnableSnowOnGround` | boolean; code default `true`; Apocalypse `true` | If snow will accumulate on the ground. If disabled, snow will still show on vegetation and rooftops. | Independent/no hard gate identified |
| **Melee Movement Disruption**<br>`AttackBlockMovements` | boolean; code default `true`; Apocalypse `true` | If melee attacking slows you down. | Independent/no hard gate identified |
| **Randomized Building Chance**<br>`SurvivorHouseChance` | enum 1–7; code default `3`; Apocalypse `3` | The chance of finding randomized buildings on the map (eg. burnt out houses, ones containing loot stashes or dead bodies). Values: 1=Never; 2=Extremely Rare; 3=Rare; 4=Sometimes; 5=Often; 6=Very Often; 7=Always Tries. | Independent/no hard gate identified |
| **All Clothing Unlocked**<br>`AllClothesUnlocked` | boolean; code default `false`; Apocalypse `false` | Allows you to select from every piece of clothing in the game when customizing your character | Independent/no hard gate identified |
| **Enable 'Tainted Water' tooltip**<br>`EnableTaintedWaterText` | boolean; code default `true`; Apocalypse `true` | If tainted water will show a warning marking it as such. | Independent/no hard gate identified |
| **Zombie Attraction Multiplier**<br>`ZombieAttractionMultiplier` | double 0.0–100.0; code default `1.0`; Apocalypse `1.0` | General engine loudness to zombies. | Independent/no hard gate identified |
| **Player Damage from Crash**<br>`PlayerDamageFromCrash` | boolean; code default `true`; Apocalypse `true` | If the player can get injured from being in a car accident. | Independent/no hard gate identified |
| **Weapon Multi Hit**<br>`MultiHitZombies` | boolean; code default `false`; Apocalypse `false` | If certain melee weapons will be able to strike multiple zombies in one hit. | Independent/no hard gate identified |
| **Rear Vulnerability**<br>`RearVulnerability` | enum 1–3; code default `3`; Apocalypse `3` | Chance of being bitten when a zombie attacks from behind. Values: 1=Low; 2=Medium; 3=High. | Independent/no hard gate identified |
| **Farms not on Ground Level [!]**<br>`PlaceDirtAboveground` | boolean; code default `false`; Apocalypse `false` | <BHC> [!] It is recommended that you DO NOT change this. Changing this can result in performance issues. [!] <RGB:1,1,1> When enabled, dirt can be placed, and farming performed on other than the ground level. | Independent/no hard gate identified |
| **No Black Clothes**<br>`NoBlackClothes` | boolean; code default `true`; Apocalypse `true` | If true clothing with randomized tints will not be so dark to be virtually black. | Independent/no hard gate identified |
| **Easy Climbing**<br>`EasyClimbing` | boolean; code default `false`; Apocalypse `false` | Disables the failure chances when climbing sheet ropes or over walls. | Independent/no hard gate identified |

## Source and audit notes

- Registry and constructor defaults: `C:\Games\Steam\steamapps\common\ProjectZomboid\zombie_decompiled\zombie\SandboxOptions.java`.
- English UI labels, enum names, and tooltips: `C:\Games\Steam\steamapps\common\ProjectZomboid\media\lua\shared\Translate\EN\Sandbox.json`.
- Apocalypse preset comparison: `C:\Games\Steam\steamapps\common\ProjectZomboid\media\lua\shared\Sandbox\Apocalypse.lua`.
- Runtime consumers were traced in the installed decompiled Java tree and vanilla Lua. A tooltip is used where it accurately describes the terminal calculation; explicit notes override it where several controls feed one calculation.
- Principal implementation sites include `zombie/inventory/ItemPickerJava.java` (loot multipliers, rolls, diminishing loot and removal), `zombie/randomizedWorld/randomizedBuilding/RBLooted.java` (pre-looted buildings), `zombie/popman/ZombiePopulationManager.java` and `zombie/characters/ZombieGroup.java` (population, respawn, migration and rally groups), and `zombie/characters/animals/datas/AnimalData.java` (animal growth/reproduction products).
- `SandboxOptions.java` is authoritative for what is a vanilla sandbox option. Third-party `media/sandbox-options.txt` entries are deliberately excluded.

### Screenshot provenance

The controls shown in the supplied screenshot are vanilla Build 42.19 controls: the diminished/pre-looted-building settings and expanded category rarity fields are registered directly by `SandboxOptions.java`. They are not being mistaken for the installed Better Containers or other workshop options.

### Coverage check

- Parsed runtime options: **269**.
- Rows written: **269**.
- Unique raw IDs: **269** (duplicates: **0**).

