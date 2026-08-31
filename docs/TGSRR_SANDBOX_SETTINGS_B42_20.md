# TGSRR Sandbox Settings - Build 42.20

This table records the canonical shared sandbox baseline used by every TGSRR challenge and by the selectable **Unofficial TGSRR** Custom Sandbox preset.

- Canonical source: `Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/shared/TGSRR/Sandbox/Base.lua`
- Vanilla 42.19 registry: legacy decompile `PZJava/PZ_Java_B42_19`
- Vanilla 42.20 registry: authoritative decompile Steam build `24449119`
- Captured: 2026-07-30
- Coverage: all 269 vanilla settings, plus 23 TGSRR custom settings documented
  separately as Rat Race Stable additions
- Challenge-specific deltas are applied after this baseline. For example, TGSRR CDDA changes `TimeSinceApo` from `1` to `13`.
- **Vanilla 42.19** and **Vanilla 42.20** record each build's constructor
  default, not a named vanilla preset such as Apocalypse.
- **Unstable** records the TGSRR Build 42.19 challenge/preset value.
- **Stable** records agreed replacement values for the Build 42.20 ruleset and
  remains blank where no replacement has been agreed.

## World-item removal

`WorldItemRemovalList` is recorded separately because its long value makes the
comparison table difficult to read.

- **Vanilla 42.19:** `Base.Hat`, `Base.Glasses`, `Base.Dung_Turkey`,
  `Base.Dung_Chicken`, `Base.Dung_Cow`, `Base.Dung_Deer`, `Base.Dung_Mouse`,
  `Base.Dung_Pig`, `Base.Dung_Rabbit`, `Base.Dung_Rat`, `Base.Dung_Sheep`
- **Unstable:** `Base.Hat`, `Base.Glasses`, `Base.Maggots`, `Base.Slug`,
  `Base.Slug2`, `Base.Snail`, `Base.Worm`, `Base.Dung_Mouse`, `Base.Dung_Rat`
- **Vanilla 42.20:** `Base.Hat`, `Base.Glasses`, `Base.Dung_Turkey`,
  `Base.Dung_Chicken`, `Base.Dung_Cow`, `Base.Dung_Deer`, `Base.Dung_Mouse`,
  `Base.Dung_Pig`, `Base.Dung_Rabbit`, `Base.Dung_Rat`, `Base.Dung_Sheep`
- **Stable:** To be supplied by a Build 42.20 companion mod that lets players
  customize their own world-item removal list.
- **Remarks:** The companion mod and its canonical integration entry still need
  to be defined.

## Rat Race Stable additions

These settings are owned by TGSRR and are added for Rat Race Stable. They are
not inherited from the Unstable baseline.

| Setting | Stable | Remarks |
|---|---:|---|
| `TGSRRAlarmDecay.Enabled` | `true` | Enables the standalone Lua alarm lifecycle. Vanilla chooses alarmed buildings and supplies the alarm event, while TGSRR persists and enforces the custom expiry range without writing the inaccessible Java `BuildingDef.alarmDecay` field |
| `TGSRRAlarmDecay.MaximumDay` | `730` | Latest possible battery shutoff: two years after the power shuts off |
| `TGSRRAlarmDecay.MinimumDay` | `0` | Earliest possible battery shutoff: immediately after the power shuts off |
| `TGSRRHelicopter.DayMaximum` | `10` | Exclusive maximum world-day delay from the challenge start day within each scheduled month slot |
| `TGSRRHelicopter.DayMinimum` | `6` | Minimum world-day delay from the challenge start day within each scheduled month slot |
| `TGSRRHelicopter.DurationMaximum` | `4` | Maximum activation-opportunity window in hours; does not control flight duration |
| `TGSRRHelicopter.DurationMinimum` | `1` | Minimum activation-opportunity window in hours; does not control flight duration |
| `TGSRRHelicopter.Enabled` | `true` | Replaces vanilla recurrence with the TGSRR schedule while retaining the vanilla helicopter event |
| `TGSRRHelicopter.StartHourMaximum` | `18` | Latest possible event start hour |
| `TGSRRHelicopter.StartHourMinimum` | `9` | Earliest possible event start hour |
| `TGSRRHelicopter.Year1Months` | `7` | Calendar months receiving one scheduled event in challenge year 1 |
| `TGSRRHelicopter.Year2Months` | `7,1` | Calendar months receiving one scheduled event in challenge year 2 |
| `TGSRRHelicopter.Year3Months` | `7,11,3` | Calendar months receiving one scheduled event in challenge year 3 |
| `TGSRRHelicopter.Year4Months` | `7,10,1,4` | Calendar months receiving one scheduled event in challenge year 4 |
| `TGSRRHelicopter.Year5Months` | `7,9,11,1,3` | Calendar months receiving one scheduled event in challenge year 5 |
| `TGSRRHelicopter.Year6Months` | `7,10,1,4` | Calendar months receiving one scheduled event in challenge year 6 |
| `TGSRRHelicopter.Year7Months` | `7,11,3` | Calendar months receiving one scheduled event in challenge year 7 |
| `TGSRRHelicopter.Year8Months` | `7,1` | Calendar months receiving one scheduled event in challenge year 8 |
| `TGSRRHelicopter.Year9Months` | `7` | Calendar months receiving one scheduled event in challenge year 9 |

Helicopter month slots use the challenge's original start day-of-month as
their anchor. With the default July 9 start, each configured month anchors on
the 9th. `DayMinimum = 6` and the exclusive `DayMaximum = 10` reproduce
vanilla `Rand.Next(6, 10)`, so the selected event date is the 15th through
18th. The duration settings control the activation-opportunity window, not the
helicopter's actual flight duration.
| `TGSRRRanchMortality.Enabled` | `true` | Replaces vanilla ranch mortality with TGSRR's configurable mortality rules |
| `TGSRRRanchMortality.FemaleDeathDay` | `-1` | Day females are guaranteed dead; `-1` disables female mortality |
| `TGSRRRanchMortality.MaleDeathDay` | `-1` | Day males are guaranteed dead; `-1` disables male mortality |
| `TGSRRRanchMortality.RollStartDay` | `60` | Elapsed world day after which adult mortality rolls begin |

## Settings comparison

This table compares the vanilla Build 42.20 settings inherited by Rat Race.

| Setting | Vanilla 42.19 | Unstable | Vanilla 42.20 | Stable | Remarks |
|---|---:|---:|---:|---:|---|
| **Population** |  |  |  |  |  |
| `Zombies` | `4` | `1` | `4` |  |  |
| `Distribution` | `1` | `1` | `1` |  |  |
| `ZombieVoronoiNoise` | `true` | `true` | `true` |  |  |
| `ZombieRespawn` | `2` | `4` | `2` |  |  |
| `ZombieMigrate` | `true` | `true` | `true` |  |  |
| **Advanced zombie population** |  |  |  |  |  |
| `ZombieConfig.PopulationMultiplier` | `0.65f` | `4.0` | `0.65f` |  |  |
| `ZombieConfig.PopulationStartMultiplier` | `1.0` | `4.0` | `1.0` |  |  |
| `ZombieConfig.PopulationPeakMultiplier` | `1.5` | `4.0` | `1.5` |  |  |
| `ZombieConfig.PopulationPeakDay` | `28` | `1` | `28` |  |  |
| `ZombieConfig.RespawnHours` | `72.0` | `0.0` | `72.0` |  |  |
| `ZombieConfig.RespawnUnseenHours` | `16.0` | `0.0` | `16.0` |  |  |
| `ZombieConfig.RespawnMultiplier` | `0.1` | `0.0` | `0.1` |  |  |
| `ZombieConfig.RedistributeHours` | `12.0` | `1.0` | `12.0` |  |  |
| `ZombieConfig.FollowSoundDistance` | `100` | `1000` | `100` |  |  |
| `ZombieConfig.RallyGroupSize` | `20` | `0` | `20` |  |  |
| `ZombieConfig.RallyGroupSizeVariance` | `50` | `0` | `50` |  |  |
| `ZombieConfig.RallyTravelDistance` | `20` | `50` | `20` |  |  |
| `ZombieConfig.RallyGroupSeparation` | `15` | `5` | `15` |  |  |
| `ZombieConfig.RallyGroupRadius` | `3` | `1` | `3` |  |  |
| `ZombieConfig.ZombiesCountBeforeDelete` | `300` | `300` | `300` | `0` | Agreed Rat Race value. |
| **Zombie lore and behaviour** |  |  |  |  |  |
| `ZombieLore.Speed` | `2` | `2` | `2` |  |  |
| `ZombieLore.SprinterPercentage` | `33` | `0` | `33` |  |  |
| `ZombieLore.Strength` | `2` | `2` | `2` |  |  |
| `ZombieLore.Toughness` | `2` | `2` | `2` |  |  |
| `ZombieLore.Transmission` | `1` | `1` | `1` |  |  |
| `ZombieLore.Mortality` | `5` | `5` | `5` |  |  |
| `ZombieLore.Reanimate` | `3` | `1` | `3` |  |  |
| `ZombieLore.Cognition` | `3` | `1` | `3` |  |  |
| `ZombieLore.DoorOpeningPercentage` | `33` | `0` | `33` |  |  |
| `ZombieLore.CrawlUnderVehicle` | `5` | `7` | `5` |  |  |
| `ZombieLore.Memory` | `2` | `1` | `2` |  |  |
| `ZombieLore.Sight` | `2` | `1` | `2` |  |  |
| `ZombieLore.Hearing` | `2` | `1` | `2` |  |  |
| `ZombieLore.SpottedLogic` | `true` | `true` | `true` |  |  |
| `ZombieLore.ThumpNoChasing` | `false` | `false` | `false` |  |  |
| `ZombieLore.ThumpOnConstruction` | `true` | `true` | `true` |  |  |
| `ZombieLore.ActiveOnly` | `1` | `1` | `1` |  |  |
| `ZombieLore.TriggerHouseAlarm` | `false` | `false` | `false` |  |  |
| `ZombieLore.ZombiesDragDown` | `true` | `true` | `true` |  |  |
| `ZombieLore.ZombiesCrawlersDragDown` | `false` | `true` | `false` |  |  |
| `ZombieLore.ZombiesFenceLunge` | `true` | `true` | `true` |  |  |
| `ZombieLore.ZombiesArmorFactor` | `2.0` | `2.0` | `2.0` |  |  |
| `ZombieLore.ZombiesMaxDefense` | `85` | `85` | `85` |  |  |
| `ZombieLore.ChanceOfAttachedWeapon` | `6` | `5` | `6` |  |  |
| `ZombieLore.ZombiesFallDamage` | `1.0` | `0.1` | `1.0` |  |  |
| `ZombieLore.DisableFakeDead` | `1` | `2` | `1` |  |  |
| `ZombieLore.PlayerSpawnZombieRemoval` | `1` | `4` | `1` |  |  |
| `ZombieLore.FenceThumpersRequired` | `50` | `25` | `50` |  |  |
| `ZombieLore.FenceDamageMultiplier` | `1.0` | `1.0` | `1.0` |  |  |
| **Time and climate** |  |  |  |  |  |
| `DayLength` | `4` | `3` | `4` | `4` | One full in-game day lasts 1 hour 30 minutes in real time |
| `StartYear` | `1` | `1` | `1` |  |  |
| `StartMonth` | `7` | `7` | `7` |  |  |
| `StartDay` | `23` | `9` | `23` |  |  |
| `StartTime` | `2` | `2` | `2` |  |  |
| `DayNightCycle` | `1` | `1` | `1` |  |  |
| `ClimateCycle` | `1` | `1` | `1` |  |  |
| `FogCycle` | `1` | `1` | `1` |  |  |
| `StarterKit` | `false` | `false` | `false` |  |  |
| `TimeSinceApo` | `1` | `1` | `1` |  |  |
| **Loot** |  |  |  |  |  |
| `FoodLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `LiteratureLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `SkillBookLoot` | `0.6` | `0.04` | `0.6` |  |  |
| `RecipeResourceLoot` | `0.6` | `0.04` | `0.6` |  |  |
| `MedicalLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `SurvivalGearsLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `CannedFoodLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `WeaponLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `RangedWeaponLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `AmmoLootNew` | `0.6` | `0.04` | `0.6` | `0.25` |  |
| `MechanicsLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `OtherLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `ClothingLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `ContainerLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `KeyLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `MediaLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `MementoLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `CookwareLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `MaterialLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `FarmingLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `ToolLootNew` | `0.6` | `0.04` | `0.6` |  |  |
| `RollsMultiplier` | `1.0` | `1.0` | `1.0` |  |  |
| `LootItemRemovalList` | *(empty)* | *(empty)* | *(empty)* |  |  |
| `RemoveStoryLoot` | `false` | `false` | `false` |  |  |
| `RemoveZombieLoot` | `false` | `false` | `false` |  |  |
| `ZombiePopLootEffect` | `10` | `10` | `10` |  |  |
| `InsaneLootFactor` | `0.05` | `0.05` | `0.05` |  |  |
| `ExtremeLootFactor` | `0.2` | `0.2` | `0.2` |  |  |
| `RareLootFactor` | `0.6` | `0.6` | `0.6` |  |  |
| `NormalLootFactor` | `1.0` | `1.0` | `1.0` |  |  |
| `CommonLootFactor` | `2.0` | `2.0` | `2.0` |  |  |
| `AbundantLootFactor` | `3.0` | `3.0` | `3.0` |  |  |
| `SeenHoursPreventLootRespawn` | `0` | `0` | `0` |  |  |
| `HoursForLootRespawn` | `0` | `0` | `0` |  |  |
| `MaxItemsForLootRespawn` | `5` | `5` | `5` |  |  |
| `ConstructionPreventsLootRespawn` | `true` | `true` | `true` |  |  |
| **Pre-looted and trashed buildings** |  |  |  |  |  |
| `MaximumLootedBuildingRooms` | `50` | `100` | `50` |  |  |
| `MaximumLooted` | `50` | `60` | `50` |  |  |
| `DaysUntilMaximumLooted` | `90` | `3650` | `90` |  |  |
| `RuralLooted` | `0.5` | `2.0` | `0.5` |  |  |
| **Diminished generated loot** |  |  |  |  |  |
| `MaximumDiminishedLoot` | `0` | `90` | `0` | `0` | No additional generated-loot removal; the base `0.04` loot multipliers remain fully effective. |
| `DaysUntilMaximumDiminishedLoot` | `3650` | `3650` | `3650` | `1825` | Five years. With a 0% maximum reduction, generated loot remains at the base multiplier throughout. |
| **Utilities** |  |  |  |  |  |
| `WaterShut` | `2` | `1` | `2` |  |  |
| `ElecShut` | `2` | `1` | `2` |  |  |
| `AlarmDecay` | `2` | `6` | `2` | `5` | Vanilla fallback is limited to 0-1 year for any alarm TGSRR does not claim. TGSRR-owned alarms use `TGSRRAlarmDecay.MinimumDay` and `MaximumDay`. |
| `WaterShutModifier` | `14` | `-1` | `14` |  |  |
| `ElecShutModifier` | `14` | `-1` | `14` | `3` | A 72-hour world-age threshold: power turns off just after 07:00 on Day 4, approximately 70 hours after the 09:00 Day 1 spawn. |
| `AlarmDecayModifier` | `14` | `14` | `14` |  | Registered but unused by the Build 42 alarm-decay runtime; retained legacy preset field |
| `GeneratorFuelConsumption` | `0.1` | `0.1` | `0.1` |  |  |
| `GeneratorSpawning` | `5` | `2` | `5` |  |  |
| `AllowExteriorGenerator` | `true` | `true` | `true` |  |  |
| `LightBulbLifespan` | `1.0` | `10.0` | `1.0` | `30.0` |  |
| `GeneratorTileRange` | `20` | `20` | `20` |  |  |
| `GeneratorVerticalPowerRange` | `3` | `3` | `3` |  |  |
| **World generation and stories** |  |  |  |  |  |
| `Alarm` | `4` | `6` | `4` |  |  |
| `LockedHouses` | `4` | `6` | `4` |  |  |
| `Helicopter` | `2` | `1` | `2` |  |  |
| `MetaEvent` | `2` | `1` | `2` |  |  |
| `SleepingEvent` | `1` | `1` | `1` |  |  |
| `ZoneStoryChance` | `3` | `2` | `3` |  |  |
| `Basement.SpawnFrequency` | `4` | `7` | `4` |  |  |
| **Vehicles** |  |  |  |  |  |
| `VehicleStoryChance` | `3` | `2` | `3` |  |  |
| `EnableVehicles` | `true` | `true` | `true` |  |  |
| `CarSpawnRate` | `4` | `2` | `4` |  |  |
| `VehicleEasyUse` | `false` | `false` | `false` |  |  |
| `InitialGas` | `3` | `1` | `3` |  |  |
| `FuelStationGasInfinite` | `false` | `false` | `false` |  |  |
| `FuelStationGasMin` | `0.0` | `0.0` | `0.0` |  |  |
| `FuelStationGasMax` | `0.7` | `0.05` | `0.7` |  |  |
| `FuelStationGasEmptyChance` | `20` | `25` | `20` |  |  |
| `LockedCar` | `4` | `6` | `4` |  |  |
| `CarGasConsumption` | `1.0` | `1.0` | `1.0` |  |  |
| `CarGeneralCondition` | `3` | `1` | `3` |  |  |
| `CarDamageOnImpact` | `3` | `5` | `3` |  |  |
| `DamageToPlayerFromHitByACar` | `1` | `5` | `1` |  |  |
| `TrafficJam` | `true` | `true` | `true` |  |  |
| `CarAlarm` | `4` | `6` | `4` |  |  |
| `SirenShutoffHours` | `0.0` | `1.0` | `0.0` |  |  |
| `ChanceHasGas` | `2` | `1` | `2` |  |  |
| `RecentlySurvivorVehicles` | `3` | `1` | `3` |  |  |
| `SirenEffectsZombies` | `true` | `true` | `true` |  |  |
| **Animals** |  |  |  |  |  |
| `AnimalStatsModifier` | `4` | `4` | `4` |  |  |
| `AnimalMetaStatsModifier` | `4` | `4` | `4` |  |  |
| `AnimalPregnancyTime` | `2` | `4` | `2` |  |  |
| `AnimalAgeModifier` | `3` | `4` | `3` |  |  |
| `AnimalMilkIncModifier` | `3` | `4` | `3` |  |  |
| `AnimalWoolIncModifier` | `3` | `4` | `3` |  |  |
| `AnimalRanchChance` | `7` | `2` | `7` |  |  |
| `AnimalGrassRegrowTime` | `240` | `720` | `240` |  |  |
| `AnimalMetaPredator` | `false` | `false` | `false` |  |  |
| `AnimalMatingSeason` | `true` | `true` | `true` |  |  |
| `AnimalEggHatch` | `3` | `4` | `3` |  |  |
| `AnimalSoundAttractZombies` | `false` | `true` | `false` |  |  |
| `AnimalTrackChance` | `4` | `4` | `4` |  |  |
| `AnimalPathChance` | `4` | `4` | `4` |  |  |
| `MaximumRatIndex` | `25` | `50` | `25` |  |  |
| `DaysUntilMaximumRatIndex` | `90` | `90` | `90` |  |  |
| **Farming and resources** |  |  |  |  |  |
| `Farming` | `3` | `3` | `3` |  |  |
| `CompostTime` | `2` | `8` | `2` |  |  |
| `PlantResilience` | `3` | `4` | `3` |  |  |
| `PlantAbundance` | `3` | `3` | `3` |  |  |
| `KillInsideCrops` | `true` | `true` | `true` |  |  |
| `PlantGrowingSeasons` | `true` | `true` | `true` |  |  |
| `FarmingSpeedNew` | `1.0` | `1.0` | `1.0` |  |  |
| `FarmingAmountNew` | `1.0` | `1.0` | `1.0` |  |  |
| `ClayLakeChance` | `0.05` | `0.05` | `0.05` |  |  |
| `ClayRiverChance` | `0.05` | `0.05` | `0.05` |  |  |
| **Nature, fishing and foraging** |  |  |  |  |  |
| `NatureAbundance` | `3` | `2` | `3` |  |  |
| `MaggotSpawn` | `1` | `2` | `1` |  |  |
| `FishAbundance` | `3` | `2` | `3` |  |  |
| **Player health** |  |  |  |  |  |
| `StatsDecrease` | `3` | `3` | `3` |  |  |
| `Nutrition` | `false` | `true` | `false` |  |  |
| `EndRegen` | `3` | `3` | `3` |  |  |
| `BoneFracture` | `true` | `true` | `true` |  |  |
| `InjurySeverity` | `2` | `3` | `2` |  |  |
| `EnablePoisoning` | `1` | `1` | `1` |  |  |
| `MuscleStrainFactor` | `1.0` | `1.67` | `1.0` |  |  |
| `DiscomfortFactor` | `1.0` | `2.0` | `1.0` |  |  |
| `WoundInfectionFactor` | `0.0` | `10.0` | `0.0` |  |  |
| **Character, skills and literature** |  |  |  |  |  |
| `MetaKnowledge` | `3` | `1` | `3` |  |  |
| `SeeNotLearntRecipe` | `true` | `true` | `true` |  |  |
| `LevelForMediaXPCutoff` | `3` | `3` | `3` |  |  |
| `LevelForDismantleXPCutoff` | `0` | `0` | `0` |  |  |
| `LiteratureCooldown` | `90` | `365` | `90` |  |  |
| `NegativeTraitsPenalty` | `1` | `1` | `1` |  |  |
| `MinutesPerPage` | `2.0` | `2.0` | `2.0` |  |  |
| **XP multipliers** |  |  |  |  |  |
| `MultiplierConfig.Global` | `1.0` | `0.8` | `1.0` |  |  |
| `MultiplierConfig.GlobalToggle` | `true` | `true` | `true` |  |  |
| `MultiplierConfig.Fitness` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Strength` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Sprinting` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Lightfoot` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Nimble` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Sneak` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Axe` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Blunt` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.SmallBlunt` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.LongBlade` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.SmallBlade` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Spear` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Maintenance` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Woodwork` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Cooking` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Farming` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Doctor` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Electricity` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.MetalWelding` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Mechanics` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Tailoring` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Aiming` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Reloading` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Fishing` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Trapping` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.PlantScavenging` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.FlintKnapping` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Masonry` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Pottery` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Carving` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Husbandry` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Tracking` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Blacksmith` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Butchering` | `1.0` | `1.0` | `1.0` |  |  |
| `MultiplierConfig.Glassmaking` | `1.0` | `1.0` | `1.0` |  |  |
| **Map** |  |  |  |  |  |
| `Map.AllowMiniMap` | `false` | `true` | `false` |  |  |
| `Map.AllowWorldMap` | `true` | `true` | `true` |  |  |
| `Map.MapAllKnown` | `false` | `true` | `false` |  |  |
| `Map.MapNeedsLight` | `true` | `true` | `true` |  |  |
| **Cleanup, fire and corpses** |  |  |  |  |  |
| `HoursForWorldItemRemoval` | `24.0` | `6.0` | `24.0` |  |  |
| `HoursForCorpseRemoval` | `-1.0` | `120.0` | `-1.0` |  |  |
| `DecayingCorpseHealthImpact` | `3` | `3` | `3` |  |  |
| `BloodLevel` | `3` | `5` | `3` |  |  |
| `FireSpread` | `true` | `true` | `true` |  |  |
| `DaysForRottenFoodRemoval` | `-1` | `-1` | `-1` |  |  |
| `BloodSplatLifespanDays` | `0` | `3` | `0` |  |  |
| `MaximumFireFuelHours` | `8` | `8` | `8` | `12` |  |
| `FirearmUseDamageChance` | `2` | `true` | `2` | `2` | Build 42.20 replaces the 42.19 boolean with an enum; `2` retains the intended Zombies Only behavior |
| `FirearmNoiseMultiplier` | `1.0` | `1.0` | `1.0` |  |  |
| `FirearmJamMultiplier` | `0.0` | `0.0` | `0.0` |  |  |
| `FirearmMoodleMultiplier` | `1.0` | `1.0` | `1.0` |  |  |
| `FirearmWeatherMultiplier` | `1.0` | `1.0` | `1.0` |  |  |
| `FirearmHeadGearEffect` | `true` | `true` | `true` |  |  |
| **Gameplay and miscellaneous** |  |  |  |  |  |
| `Temperature` | `3` | `1` | `3` | `3` |  |
| `Rain` | `3` | `1` | `3` | `3` |  |
| `ErosionSpeed` | `3` | `4` | `3` |  |  |
| `ErosionDays` | `0` | `0` | `0` |  |  |
| `FoodRotSpeed` | `3` | `2` | `3` |  |  |
| `FridgeFactor` | `3` | `2` | `3` |  |  |
| `ItemRemovalListBlacklistToggle` | `false` | `false` | `false` |  |  |
| `AnnotatedMapChance` | `4` | `2` | `4` |  |  |
| `CharacterFreePoints` | `0` | `0` | `0` |  |  |
| `ConstructionBonusPoints` | `3` | `3` | `3` |  |  |
| `NightDarkness` | `3` | `3` | `3` |  |  |
| `NightLength` | `3` | `3` | `3` |  |  |
| `ZombieHealthImpact` | `false` | `true` | `false` |  |  |
| `ClothingDegradation` | `3` | `4` | `3` |  |  |
| `MaxFogIntensity` | `1` | `1` | `1` |  |  |
| `MaxRainFxIntensity` | `1` | `1` | `1` |  |  |
| `EnableSnowOnGround` | `true` | `true` | `true` |  |  |
| `AttackBlockMovements` | `true` | `true` | `true` |  |  |
| `SurvivorHouseChance` | `3` | `2` | `3` |  |  |
| `AllClothesUnlocked` | `false` | `false` | `false` |  |  |
| `EnableTaintedWaterText` | `true` | `true` | `true` |  |  |
| `ZombieAttractionMultiplier` | `1.0` | `10.0` | `1.0` | `5.0` |  |
| `PlayerDamageFromCrash` | `true` | `true` | `true` |  |  |
| `MultiHitZombies` | `false` | `false` | `false` |  |  |
| `RearVulnerability` | `3` | `3` | `3` |  |  |
| `PlaceDirtAboveground` | `false` | `false` | `false` |  |  |
| `NoBlackClothes` | `true` | `true` | `true` |  |  |
| `EasyClimbing` | `false` | `false` | `false` |  |  |
