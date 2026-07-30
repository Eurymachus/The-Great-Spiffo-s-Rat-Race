# TGSRR Sandbox Settings - Build 42.20

This table records the canonical shared sandbox baseline used by every TGSRR challenge and by the selectable **Unofficial TGSRR** Custom Sandbox preset.

- Canonical source: `Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/shared/TGSRR/Sandbox/Base.lua`
- Vanilla registry: Project Zomboid Build 42.20, Steam build `24449119`
- Captured: 2026-07-30
- Coverage: all 269 vanilla settings, plus 23 TGSRR custom settings documented
  separately as Rat Race Stable additions
- Challenge-specific deltas are applied after this baseline. For example, TGSRR CDDA changes `TimeSinceApo` from `1` to `13`.
- **Unstable** records the current Build 42.20 challenge/preset value.
- **Stable** is intentionally blank until a replacement value is agreed. Only
  settings selected for the stable ruleset should be populated there.

## World-item removal

`WorldItemRemovalList` is recorded separately because its long value makes the
comparison table difficult to read.

- **Unstable:** `Base.Hat`, `Base.Glasses`, `Base.Maggots`, `Base.Slug`,
  `Base.Slug2`, `Base.Snail`, `Base.Worm`, `Base.Dung_Mouse`, `Base.Dung_Rat`
- **Stable:** To be supplied by a Build 42.20 companion mod that lets players
  customize their own world-item removal list.
- **Remarks:** The companion mod and its canonical integration entry still need
  to be defined.

## Rat Race Stable additions

These settings are owned by TGSRR and are added for Rat Race Stable. They are
not inherited from the Unstable baseline.

| Setting | Stable | Remarks |
|---|---:|---|
| `TGSRRAlarmDecay.Enabled` | `true` | Replaces vanilla alarm decay with the Rat Race Stable custom range |
| `TGSRRAlarmDecay.MaximumDay` | `730` | Latest possible battery shutoff: two years after the power shuts off |
| `TGSRRAlarmDecay.MinimumDay` | `0` | Earliest possible battery shutoff: immediately after the power shuts off |
| `TGSRRHelicopter.DayMaximum` | `14` | Latest possible day of the month for each scheduled event |
| `TGSRRHelicopter.DayMinimum` | `8` | Earliest possible day of the month for each scheduled event |
| `TGSRRHelicopter.DurationMaximum` | `4` | Maximum event-window duration in hours |
| `TGSRRHelicopter.DurationMinimum` | `1` | Minimum event-window duration in hours |
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
| `TGSRRRanchMortality.Enabled` | `true` | Replaces vanilla ranch mortality with TGSRR's configurable mortality rules |
| `TGSRRRanchMortality.FemaleDeathDay` | `-1` | Day females are guaranteed dead; `-1` disables female mortality |
| `TGSRRRanchMortality.MaleDeathDay` | `-1` | Day males are guaranteed dead; `-1` disables male mortality |
| `TGSRRRanchMortality.RollStartDay` | `60` | Elapsed world day after which adult mortality rolls begin |

## Settings comparison

This table compares the vanilla Build 42.20 settings inherited by Rat Race.

| Setting | Unstable | Stable | Remarks |
|---|---:|---:|---|
| **Population** |  |  |  |
| `Zombies` | `1` |  |  |
| `Distribution` | `1` |  |  |
| `ZombieVoronoiNoise` | `true` |  |  |
| `ZombieRespawn` | `4` |  |  |
| `ZombieMigrate` | `true` |  |  |
| **Advanced zombie population** |  |  |  |
| `ZombieConfig.PopulationMultiplier` | `4.0` |  |  |
| `ZombieConfig.PopulationStartMultiplier` | `4.0` |  |  |
| `ZombieConfig.PopulationPeakMultiplier` | `4.0` |  |  |
| `ZombieConfig.PopulationPeakDay` | `1` |  |  |
| `ZombieConfig.RespawnHours` | `0.0` |  |  |
| `ZombieConfig.RespawnUnseenHours` | `0.0` |  |  |
| `ZombieConfig.RespawnMultiplier` | `0.0` |  |  |
| `ZombieConfig.RedistributeHours` | `1.0` |  |  |
| `ZombieConfig.FollowSoundDistance` | `1000` |  |  |
| `ZombieConfig.RallyGroupSize` | `0` |  |  |
| `ZombieConfig.RallyGroupSizeVariance` | `0` |  |  |
| `ZombieConfig.RallyTravelDistance` | `50` |  |  |
| `ZombieConfig.RallyGroupSeparation` | `5` |  |  |
| `ZombieConfig.RallyGroupRadius` | `1` |  |  |
| `ZombieConfig.ZombiesCountBeforeDelete` | `300` |  |  |
| **Zombie lore and behaviour** |  |  |  |
| `ZombieLore.Speed` | `2` |  |  |
| `ZombieLore.SprinterPercentage` | `0` |  |  |
| `ZombieLore.Strength` | `2` |  |  |
| `ZombieLore.Toughness` | `2` |  |  |
| `ZombieLore.Transmission` | `1` |  |  |
| `ZombieLore.Mortality` | `5` |  |  |
| `ZombieLore.Reanimate` | `1` |  |  |
| `ZombieLore.Cognition` | `1` |  |  |
| `ZombieLore.DoorOpeningPercentage` | `0` |  |  |
| `ZombieLore.CrawlUnderVehicle` | `7` |  |  |
| `ZombieLore.Memory` | `1` |  |  |
| `ZombieLore.Sight` | `1` |  |  |
| `ZombieLore.Hearing` | `1` |  |  |
| `ZombieLore.SpottedLogic` | `true` |  |  |
| `ZombieLore.ThumpNoChasing` | `false` |  |  |
| `ZombieLore.ThumpOnConstruction` | `true` |  |  |
| `ZombieLore.ActiveOnly` | `1` |  |  |
| `ZombieLore.TriggerHouseAlarm` | `false` |  |  |
| `ZombieLore.ZombiesDragDown` | `true` |  |  |
| `ZombieLore.ZombiesCrawlersDragDown` | `true` |  |  |
| `ZombieLore.ZombiesFenceLunge` | `true` |  |  |
| `ZombieLore.ZombiesArmorFactor` | `2.0` |  |  |
| `ZombieLore.ZombiesMaxDefense` | `85` |  |  |
| `ZombieLore.ChanceOfAttachedWeapon` | `5` |  |  |
| `ZombieLore.ZombiesFallDamage` | `0.1` |  |  |
| `ZombieLore.DisableFakeDead` | `2` |  |  |
| `ZombieLore.PlayerSpawnZombieRemoval` | `4` |  |  |
| `ZombieLore.FenceThumpersRequired` | `25` |  |  |
| `ZombieLore.FenceDamageMultiplier` | `1.0` |  |  |
| **Time and climate** |  |  |  |
| `DayLength` | `3` | `4` | One full in-game day lasts 1 hour 30 minutes in real time |
| `StartYear` | `1` |  |  |
| `StartMonth` | `7` |  |  |
| `StartDay` | `9` |  |  |
| `StartTime` | `2` |  |  |
| `DayNightCycle` | `1` |  |  |
| `ClimateCycle` | `1` |  |  |
| `FogCycle` | `1` |  |  |
| `StarterKit` | `false` |  |  |
| `TimeSinceApo` | `1` |  |  |
| **Loot** |  |  |  |
| `FoodLootNew` | `0.04` |  |  |
| `LiteratureLootNew` | `0.04` |  |  |
| `SkillBookLoot` | `0.04` |  |  |
| `RecipeResourceLoot` | `0.04` |  |  |
| `MedicalLootNew` | `0.04` |  |  |
| `SurvivalGearsLootNew` | `0.04` |  |  |
| `CannedFoodLootNew` | `0.04` |  |  |
| `WeaponLootNew` | `0.04` |  |  |
| `RangedWeaponLootNew` | `0.04` |  |  |
| `AmmoLootNew` | `0.04` |  |  |
| `MechanicsLootNew` | `0.04` |  |  |
| `OtherLootNew` | `0.04` |  |  |
| `ClothingLootNew` | `0.04` |  |  |
| `ContainerLootNew` | `0.04` |  |  |
| `KeyLootNew` | `0.04` |  |  |
| `MediaLootNew` | `0.04` |  |  |
| `MementoLootNew` | `0.04` |  |  |
| `CookwareLootNew` | `0.04` |  |  |
| `MaterialLootNew` | `0.04` |  |  |
| `FarmingLootNew` | `0.04` |  |  |
| `ToolLootNew` | `0.04` |  |  |
| `RollsMultiplier` | `1.0` |  |  |
| `LootItemRemovalList` | *(empty)* |  |  |
| `RemoveStoryLoot` | `false` |  |  |
| `RemoveZombieLoot` | `false` |  |  |
| `ZombiePopLootEffect` | `10` |  |  |
| `InsaneLootFactor` | `0.05` |  |  |
| `ExtremeLootFactor` | `0.2` |  |  |
| `RareLootFactor` | `0.6` |  |  |
| `NormalLootFactor` | `1.0` |  |  |
| `CommonLootFactor` | `2.0` |  |  |
| `AbundantLootFactor` | `3.0` |  |  |
| `SeenHoursPreventLootRespawn` | `0` |  |  |
| `HoursForLootRespawn` | `0` |  |  |
| `MaxItemsForLootRespawn` | `5` |  |  |
| `ConstructionPreventsLootRespawn` | `true` |  |  |
| **Pre-looted and trashed buildings** |  |  |  |
| `MaximumLootedBuildingRooms` | `100` |  |  |
| `MaximumLooted` | `60` |  |  |
| `DaysUntilMaximumLooted` | `3650` |  |  |
| `RuralLooted` | `2.0` |  |  |
| **Diminished generated loot** |  |  |  |
| `MaximumDiminishedLoot` | `90` |  |  |
| `DaysUntilMaximumDiminishedLoot` | `3650` |  |  |
| **Utilities** |  |  |  |
| `WaterShut` | `1` |  |  |
| `ElecShut` | `1` |  |  |
| `AlarmDecay` | `6` |  |  |
| `WaterShutModifier` | `-1` |  |  |
| `ElecShutModifier` | `-1` |  |  |
| `AlarmDecayModifier` | `14` |  | Registered but unused by the Build 42 alarm-decay runtime; retained legacy preset field |
| `GeneratorFuelConsumption` | `0.1` |  |  |
| `GeneratorSpawning` | `2` |  |  |
| `AllowExteriorGenerator` | `true` |  |  |
| `LightBulbLifespan` | `10.0` | `30.0` |  |
| `GeneratorTileRange` | `20` |  |  |
| `GeneratorVerticalPowerRange` | `3` |  |  |
| **World generation and stories** |  |  |  |
| `Alarm` | `6` |  |  |
| `LockedHouses` | `6` |  |  |
| `Helicopter` | `1` |  |  |
| `MetaEvent` | `1` |  |  |
| `SleepingEvent` | `1` |  |  |
| `ZoneStoryChance` | `2` |  |  |
| `Basement.SpawnFrequency` | `7` |  |  |
| **Vehicles** |  |  |  |
| `VehicleStoryChance` | `2` |  |  |
| `EnableVehicles` | `true` |  |  |
| `CarSpawnRate` | `2` |  |  |
| `VehicleEasyUse` | `false` |  |  |
| `InitialGas` | `1` |  |  |
| `FuelStationGasInfinite` | `false` |  |  |
| `FuelStationGasMin` | `0.0` |  |  |
| `FuelStationGasMax` | `0.05` |  |  |
| `FuelStationGasEmptyChance` | `25` |  |  |
| `LockedCar` | `6` |  |  |
| `CarGasConsumption` | `1.0` |  |  |
| `CarGeneralCondition` | `1` |  |  |
| `CarDamageOnImpact` | `5` |  |  |
| `DamageToPlayerFromHitByACar` | `5` |  |  |
| `TrafficJam` | `true` |  |  |
| `CarAlarm` | `6` |  |  |
| `SirenShutoffHours` | `1.0` |  |  |
| `ChanceHasGas` | `1` |  |  |
| `RecentlySurvivorVehicles` | `1` |  |  |
| `SirenEffectsZombies` | `true` |  |  |
| **Animals** |  |  |  |
| `AnimalStatsModifier` | `4` |  |  |
| `AnimalMetaStatsModifier` | `4` |  |  |
| `AnimalPregnancyTime` | `4` |  |  |
| `AnimalAgeModifier` | `4` |  |  |
| `AnimalMilkIncModifier` | `4` |  |  |
| `AnimalWoolIncModifier` | `4` |  |  |
| `AnimalRanchChance` | `2` |  |  |
| `AnimalGrassRegrowTime` | `720` |  |  |
| `AnimalMetaPredator` | `false` |  |  |
| `AnimalMatingSeason` | `true` |  |  |
| `AnimalEggHatch` | `4` |  |  |
| `AnimalSoundAttractZombies` | `true` |  |  |
| `AnimalTrackChance` | `4` |  |  |
| `AnimalPathChance` | `4` |  |  |
| `MaximumRatIndex` | `50` |  |  |
| `DaysUntilMaximumRatIndex` | `90` |  |  |
| **Farming and resources** |  |  |  |
| `Farming` | `3` |  |  |
| `CompostTime` | `8` |  |  |
| `PlantResilience` | `4` |  |  |
| `PlantAbundance` | `3` |  |  |
| `KillInsideCrops` | `true` |  |  |
| `PlantGrowingSeasons` | `true` |  |  |
| `FarmingSpeedNew` | `1.0` |  |  |
| `FarmingAmountNew` | `1.0` |  |  |
| `ClayLakeChance` | `0.05` |  |  |
| `ClayRiverChance` | `0.05` |  |  |
| **Nature, fishing and foraging** |  |  |  |
| `NatureAbundance` | `2` |  |  |
| `MaggotSpawn` | `2` |  |  |
| `FishAbundance` | `2` |  |  |
| **Player health** |  |  |  |
| `StatsDecrease` | `3` |  |  |
| `Nutrition` | `true` |  |  |
| `EndRegen` | `3` |  |  |
| `BoneFracture` | `true` |  |  |
| `InjurySeverity` | `3` |  |  |
| `EnablePoisoning` | `1` |  |  |
| `MuscleStrainFactor` | `1.67` |  |  |
| `DiscomfortFactor` | `2.0` |  |  |
| `WoundInfectionFactor` | `10.0` |  |  |
| **Character, skills and literature** |  |  |  |
| `MetaKnowledge` | `1` |  |  |
| `SeeNotLearntRecipe` | `true` |  |  |
| `LevelForMediaXPCutoff` | `3` |  |  |
| `LevelForDismantleXPCutoff` | `0` |  |  |
| `LiteratureCooldown` | `365` |  |  |
| `NegativeTraitsPenalty` | `1` |  |  |
| `MinutesPerPage` | `2.0` |  |  |
| **XP multipliers** |  |  |  |
| `MultiplierConfig.Global` | `0.8` |  |  |
| `MultiplierConfig.GlobalToggle` | `true` |  |  |
| `MultiplierConfig.Fitness` | `1.0` |  |  |
| `MultiplierConfig.Strength` | `1.0` |  |  |
| `MultiplierConfig.Sprinting` | `1.0` |  |  |
| `MultiplierConfig.Lightfoot` | `1.0` |  |  |
| `MultiplierConfig.Nimble` | `1.0` |  |  |
| `MultiplierConfig.Sneak` | `1.0` |  |  |
| `MultiplierConfig.Axe` | `1.0` |  |  |
| `MultiplierConfig.Blunt` | `1.0` |  |  |
| `MultiplierConfig.SmallBlunt` | `1.0` |  |  |
| `MultiplierConfig.LongBlade` | `1.0` |  |  |
| `MultiplierConfig.SmallBlade` | `1.0` |  |  |
| `MultiplierConfig.Spear` | `1.0` |  |  |
| `MultiplierConfig.Maintenance` | `1.0` |  |  |
| `MultiplierConfig.Woodwork` | `1.0` |  |  |
| `MultiplierConfig.Cooking` | `1.0` |  |  |
| `MultiplierConfig.Farming` | `1.0` |  |  |
| `MultiplierConfig.Doctor` | `1.0` |  |  |
| `MultiplierConfig.Electricity` | `1.0` |  |  |
| `MultiplierConfig.MetalWelding` | `1.0` |  |  |
| `MultiplierConfig.Mechanics` | `1.0` |  |  |
| `MultiplierConfig.Tailoring` | `1.0` |  |  |
| `MultiplierConfig.Aiming` | `1.0` |  |  |
| `MultiplierConfig.Reloading` | `1.0` |  |  |
| `MultiplierConfig.Fishing` | `1.0` |  |  |
| `MultiplierConfig.Trapping` | `1.0` |  |  |
| `MultiplierConfig.PlantScavenging` | `1.0` |  |  |
| `MultiplierConfig.FlintKnapping` | `1.0` |  |  |
| `MultiplierConfig.Masonry` | `1.0` |  |  |
| `MultiplierConfig.Pottery` | `1.0` |  |  |
| `MultiplierConfig.Carving` | `1.0` |  |  |
| `MultiplierConfig.Husbandry` | `1.0` |  |  |
| `MultiplierConfig.Tracking` | `1.0` |  |  |
| `MultiplierConfig.Blacksmith` | `1.0` |  |  |
| `MultiplierConfig.Butchering` | `1.0` |  |  |
| `MultiplierConfig.Glassmaking` | `1.0` |  |  |
| **Map** |  |  |  |
| `Map.AllowMiniMap` | `true` |  |  |
| `Map.AllowWorldMap` | `true` |  |  |
| `Map.MapAllKnown` | `true` |  |  |
| `Map.MapNeedsLight` | `true` |  |  |
| **Cleanup, fire and corpses** |  |  |  |
| `HoursForWorldItemRemoval` | `6.0` |  |  |
| `HoursForCorpseRemoval` | `120.0` |  |  |
| `DecayingCorpseHealthImpact` | `3` |  |  |
| `BloodLevel` | `5` |  |  |
| `FireSpread` | `true` |  |  |
| `DaysForRottenFoodRemoval` | `-1` |  |  |
| `BloodSplatLifespanDays` | `3` |  |  |
| `MaximumFireFuelHours` | `8` | `12` |  |
| `FirearmUseDamageChance` | `2` |  |  |
| `FirearmNoiseMultiplier` | `1.0` |  |  |
| `FirearmJamMultiplier` | `0.0` |  |  |
| `FirearmMoodleMultiplier` | `1.0` |  |  |
| `FirearmWeatherMultiplier` | `1.0` |  |  |
| `FirearmHeadGearEffect` | `true` |  |  |
| **Gameplay and miscellaneous** |  |  |  |
| `Temperature` | `1` |  |  |
| `Rain` | `1` |  |  |
| `ErosionSpeed` | `4` |  |  |
| `ErosionDays` | `0` |  |  |
| `FoodRotSpeed` | `2` |  |  |
| `FridgeFactor` | `2` |  |  |
| `ItemRemovalListBlacklistToggle` | `false` |  |  |
| `AnnotatedMapChance` | `2` |  |  |
| `CharacterFreePoints` | `0` |  |  |
| `ConstructionBonusPoints` | `3` |  |  |
| `NightDarkness` | `3` |  |  |
| `NightLength` | `3` |  |  |
| `ZombieHealthImpact` | `true` |  |  |
| `ClothingDegradation` | `4` |  |  |
| `MaxFogIntensity` | `1` |  |  |
| `MaxRainFxIntensity` | `1` |  |  |
| `EnableSnowOnGround` | `true` |  |  |
| `AttackBlockMovements` | `true` |  |  |
| `SurvivorHouseChance` | `2` |  |  |
| `AllClothesUnlocked` | `false` |  |  |
| `EnableTaintedWaterText` | `true` |  |  |
| `ZombieAttractionMultiplier` | `5.0` |  |  |
| `PlayerDamageFromCrash` | `true` |  |  |
| `MultiHitZombies` | `false` |  |  |
| `RearVulnerability` | `3` |  |  |
| `PlaceDirtAboveground` | `false` |  |  |
| `NoBlackClothes` | `true` |  |  |
| `EasyClimbing` | `false` |  |  |
