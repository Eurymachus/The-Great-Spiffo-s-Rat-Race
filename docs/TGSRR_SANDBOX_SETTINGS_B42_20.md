# TGSRR Sandbox Settings — Build 42.20

This table records the canonical shared sandbox baseline used by every TGSRR challenge and by the selectable **Unofficial TGSRR** Custom Sandbox preset.

- Canonical source: `Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/shared/TGSRR/Sandbox/Base.lua`
- Vanilla registry: Project Zomboid Build 42.20, Steam build `24449119`
- Captured: 2026-07-30
- Coverage: all 269 vanilla settings, plus 20 TGSRR custom settings documented
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
| `TGSRRHelicopter.DayMaximum` | `14` | Rat Race Stable addition |
| `TGSRRHelicopter.DayMinimum` | `8` | Rat Race Stable addition |
| `TGSRRHelicopter.DurationMaximum` | `4` | Rat Race Stable addition |
| `TGSRRHelicopter.DurationMinimum` | `1` | Rat Race Stable addition |
| `TGSRRHelicopter.Enabled` | `true` | Rat Race Stable addition |
| `TGSRRHelicopter.StartHourMaximum` | `18` | Rat Race Stable addition |
| `TGSRRHelicopter.StartHourMinimum` | `9` | Rat Race Stable addition |
| `TGSRRHelicopter.Year1Months` | `7` | Rat Race Stable addition |
| `TGSRRHelicopter.Year2Months` | `7,1` | Rat Race Stable addition |
| `TGSRRHelicopter.Year3Months` | `7,11,3` | Rat Race Stable addition |
| `TGSRRHelicopter.Year4Months` | `7,10,1,4` | Rat Race Stable addition |
| `TGSRRHelicopter.Year5Months` | `7,9,11,1,3` | Rat Race Stable addition |
| `TGSRRHelicopter.Year6Months` | `7,10,1,4` | Rat Race Stable addition |
| `TGSRRHelicopter.Year7Months` | `7,11,3` | Rat Race Stable addition |
| `TGSRRHelicopter.Year8Months` | `7,1` | Rat Race Stable addition |
| `TGSRRHelicopter.Year9Months` | `7` | Rat Race Stable addition |
| `TGSRRRanchMortality.Enabled` | `true` | Rat Race Stable addition |
| `TGSRRRanchMortality.FemaleDeathDay` | `-1` | Rat Race Stable addition |
| `TGSRRRanchMortality.MaleDeathDay` | `-1` | Rat Race Stable addition |
| `TGSRRRanchMortality.RollStartDay` | `60` | Rat Race Stable addition |

## Settings comparison

This table compares the vanilla Build 42.20 settings inherited by Rat Race.

| Setting | Unstable | Stable | Remarks |
|---|---:|---:|---|
| `AbundantLootFactor` | `3.0` |  |  |
| `Alarm` | `6` |  |  |
| `AlarmDecay` | `6` |  |  |
| `AlarmDecayModifier` | `14` |  |  |
| `AllClothesUnlocked` | `false` |  |  |
| `AllowExteriorGenerator` | `true` |  |  |
| `AmmoLootNew` | `0.04` |  |  |
| `AnimalAgeModifier` | `4` |  |  |
| `AnimalEggHatch` | `4` |  |  |
| `AnimalGrassRegrowTime` | `720` |  |  |
| `AnimalMatingSeason` | `true` |  |  |
| `AnimalMetaPredator` | `false` |  |  |
| `AnimalMetaStatsModifier` | `4` |  |  |
| `AnimalMilkIncModifier` | `4` |  |  |
| `AnimalPathChance` | `4` |  |  |
| `AnimalPregnancyTime` | `4` |  |  |
| `AnimalRanchChance` | `2` |  |  |
| `AnimalSoundAttractZombies` | `true` |  |  |
| `AnimalStatsModifier` | `4` |  |  |
| `AnimalTrackChance` | `4` |  |  |
| `AnimalWoolIncModifier` | `4` |  |  |
| `AnnotatedMapChance` | `2` |  |  |
| `AttackBlockMovements` | `true` |  |  |
| `Basement.SpawnFrequency` | `7` |  |  |
| `BloodLevel` | `5` |  |  |
| `BloodSplatLifespanDays` | `3` |  |  |
| `BoneFracture` | `true` |  |  |
| `CannedFoodLootNew` | `0.04` |  |  |
| `CarAlarm` | `6` |  |  |
| `CarDamageOnImpact` | `5` |  |  |
| `CarGasConsumption` | `1.0` |  |  |
| `CarGeneralCondition` | `1` |  |  |
| `CarSpawnRate` | `2` |  |  |
| `ChanceHasGas` | `1` |  |  |
| `CharacterFreePoints` | `0` |  |  |
| `ClayLakeChance` | `0.05` |  |  |
| `ClayRiverChance` | `0.05` |  |  |
| `ClimateCycle` | `1` |  |  |
| `ClothingDegradation` | `4` |  |  |
| `ClothingLootNew` | `0.04` |  |  |
| `CommonLootFactor` | `2.0` |  |  |
| `CompostTime` | `8` |  |  |
| `ConstructionBonusPoints` | `3` |  |  |
| `ConstructionPreventsLootRespawn` | `true` |  |  |
| `ContainerLootNew` | `0.04` |  |  |
| `CookwareLootNew` | `0.04` |  |  |
| `DamageToPlayerFromHitByACar` | `5` |  |  |
| `DayLength` | `3` |  |  |
| `DayNightCycle` | `1` |  |  |
| `DaysForRottenFoodRemoval` | `-1` |  |  |
| `DaysUntilMaximumDiminishedLoot` | `3650` |  |  |
| `DaysUntilMaximumLooted` | `3650` |  |  |
| `DaysUntilMaximumRatIndex` | `90` |  |  |
| `DecayingCorpseHealthImpact` | `3` |  |  |
| `DiscomfortFactor` | `2.0` |  |  |
| `Distribution` | `1` |  |  |
| `EasyClimbing` | `false` |  |  |
| `ElecShut` | `1` |  |  |
| `ElecShutModifier` | `-1` |  |  |
| `EnablePoisoning` | `1` |  |  |
| `EnableSnowOnGround` | `true` |  |  |
| `EnableTaintedWaterText` | `true` |  |  |
| `EnableVehicles` | `true` |  |  |
| `EndRegen` | `3` |  |  |
| `ErosionDays` | `0` |  |  |
| `ErosionSpeed` | `4` |  |  |
| `ExtremeLootFactor` | `0.2` |  |  |
| `Farming` | `3` |  |  |
| `FarmingAmountNew` | `1.0` |  |  |
| `FarmingLootNew` | `0.04` |  |  |
| `FarmingSpeedNew` | `1.0` |  |  |
| `FirearmHeadGearEffect` | `true` |  |  |
| `FirearmJamMultiplier` | `0.0` |  |  |
| `FirearmMoodleMultiplier` | `1.0` |  |  |
| `FirearmNoiseMultiplier` | `1.0` |  |  |
| `FirearmUseDamageChance` | `2` |  |  |
| `FirearmWeatherMultiplier` | `1.0` |  |  |
| `FireSpread` | `true` |  |  |
| `FishAbundance` | `2` |  |  |
| `FogCycle` | `1` |  |  |
| `FoodLootNew` | `0.04` |  |  |
| `FoodRotSpeed` | `2` |  |  |
| `FridgeFactor` | `2` |  |  |
| `FuelStationGasEmptyChance` | `25` |  |  |
| `FuelStationGasInfinite` | `false` |  |  |
| `FuelStationGasMax` | `0.05` |  |  |
| `FuelStationGasMin` | `0.0` |  |  |
| `GeneratorFuelConsumption` | `0.1` |  |  |
| `GeneratorSpawning` | `2` |  |  |
| `GeneratorTileRange` | `20` |  |  |
| `GeneratorVerticalPowerRange` | `3` |  |  |
| `Helicopter` | `1` |  |  |
| `HoursForCorpseRemoval` | `120.0` |  |  |
| `HoursForLootRespawn` | `0` |  |  |
| `HoursForWorldItemRemoval` | `6.0` |  |  |
| `InitialGas` | `1` |  |  |
| `InjurySeverity` | `3` |  |  |
| `InsaneLootFactor` | `0.05` |  |  |
| `ItemRemovalListBlacklistToggle` | `false` |  |  |
| `KeyLootNew` | `0.04` |  |  |
| `KillInsideCrops` | `true` |  |  |
| `LevelForDismantleXPCutoff` | `0` |  |  |
| `LevelForMediaXPCutoff` | `3` |  |  |
| `LightBulbLifespan` | `10.0` |  |  |
| `LiteratureCooldown` | `365` |  |  |
| `LiteratureLootNew` | `0.04` |  |  |
| `LockedCar` | `6` |  |  |
| `LockedHouses` | `6` |  |  |
| `LootItemRemovalList` | *(empty)* |  |  |
| `MaggotSpawn` | `2` |  |  |
| `Map.AllowMiniMap` | `true` |  |  |
| `Map.AllowWorldMap` | `true` |  |  |
| `Map.MapAllKnown` | `true` |  |  |
| `Map.MapNeedsLight` | `true` |  |  |
| `MaterialLootNew` | `0.04` |  |  |
| `MaxFogIntensity` | `1` |  |  |
| `MaximumDiminishedLoot` | `90` |  |  |
| `MaximumFireFuelHours` | `8` |  |  |
| `MaximumLooted` | `60` |  |  |
| `MaximumLootedBuildingRooms` | `100` |  |  |
| `MaximumRatIndex` | `50` |  |  |
| `MaxItemsForLootRespawn` | `5` |  |  |
| `MaxRainFxIntensity` | `1` |  |  |
| `MechanicsLootNew` | `0.04` |  |  |
| `MediaLootNew` | `0.04` |  |  |
| `MedicalLootNew` | `0.04` |  |  |
| `MementoLootNew` | `0.04` |  |  |
| `MetaEvent` | `1` |  |  |
| `MetaKnowledge` | `1` |  |  |
| `MinutesPerPage` | `2.0` |  |  |
| `MultiHitZombies` | `false` |  |  |
| `MultiplierConfig.Aiming` | `1.0` |  |  |
| `MultiplierConfig.Axe` | `1.0` |  |  |
| `MultiplierConfig.Blacksmith` | `1.0` |  |  |
| `MultiplierConfig.Blunt` | `1.0` |  |  |
| `MultiplierConfig.Butchering` | `1.0` |  |  |
| `MultiplierConfig.Carving` | `1.0` |  |  |
| `MultiplierConfig.Cooking` | `1.0` |  |  |
| `MultiplierConfig.Doctor` | `1.0` |  |  |
| `MultiplierConfig.Electricity` | `1.0` |  |  |
| `MultiplierConfig.Farming` | `1.0` |  |  |
| `MultiplierConfig.Fishing` | `1.0` |  |  |
| `MultiplierConfig.Fitness` | `1.0` |  |  |
| `MultiplierConfig.FlintKnapping` | `1.0` |  |  |
| `MultiplierConfig.Glassmaking` | `1.0` |  |  |
| `MultiplierConfig.Global` | `0.8` |  |  |
| `MultiplierConfig.GlobalToggle` | `true` |  |  |
| `MultiplierConfig.Husbandry` | `1.0` |  |  |
| `MultiplierConfig.Lightfoot` | `1.0` |  |  |
| `MultiplierConfig.LongBlade` | `1.0` |  |  |
| `MultiplierConfig.Maintenance` | `1.0` |  |  |
| `MultiplierConfig.Masonry` | `1.0` |  |  |
| `MultiplierConfig.Mechanics` | `1.0` |  |  |
| `MultiplierConfig.MetalWelding` | `1.0` |  |  |
| `MultiplierConfig.Nimble` | `1.0` |  |  |
| `MultiplierConfig.PlantScavenging` | `1.0` |  |  |
| `MultiplierConfig.Pottery` | `1.0` |  |  |
| `MultiplierConfig.Reloading` | `1.0` |  |  |
| `MultiplierConfig.SmallBlade` | `1.0` |  |  |
| `MultiplierConfig.SmallBlunt` | `1.0` |  |  |
| `MultiplierConfig.Sneak` | `1.0` |  |  |
| `MultiplierConfig.Spear` | `1.0` |  |  |
| `MultiplierConfig.Sprinting` | `1.0` |  |  |
| `MultiplierConfig.Strength` | `1.0` |  |  |
| `MultiplierConfig.Tailoring` | `1.0` |  |  |
| `MultiplierConfig.Tracking` | `1.0` |  |  |
| `MultiplierConfig.Trapping` | `1.0` |  |  |
| `MultiplierConfig.Woodwork` | `1.0` |  |  |
| `MuscleStrainFactor` | `1.67` |  |  |
| `NatureAbundance` | `2` |  |  |
| `NegativeTraitsPenalty` | `1` |  |  |
| `NightDarkness` | `3` |  |  |
| `NightLength` | `3` |  |  |
| `NoBlackClothes` | `true` |  |  |
| `NormalLootFactor` | `1.0` |  |  |
| `Nutrition` | `true` |  |  |
| `OtherLootNew` | `0.04` |  |  |
| `PlaceDirtAboveground` | `false` |  |  |
| `PlantAbundance` | `3` |  |  |
| `PlantGrowingSeasons` | `true` |  |  |
| `PlantResilience` | `4` |  |  |
| `PlayerDamageFromCrash` | `true` |  |  |
| `Rain` | `1` |  |  |
| `RangedWeaponLootNew` | `0.04` |  |  |
| `RareLootFactor` | `0.6` |  |  |
| `RearVulnerability` | `3` |  |  |
| `RecentlySurvivorVehicles` | `1` |  |  |
| `RecipeResourceLoot` | `0.04` |  |  |
| `RemoveStoryLoot` | `false` |  |  |
| `RemoveZombieLoot` | `false` |  |  |
| `RollsMultiplier` | `1.0` |  |  |
| `RuralLooted` | `2.0` |  |  |
| `SeenHoursPreventLootRespawn` | `0` |  |  |
| `SeeNotLearntRecipe` | `true` |  |  |
| `SirenEffectsZombies` | `true` |  |  |
| `SirenShutoffHours` | `1.0` |  |  |
| `SkillBookLoot` | `0.04` |  |  |
| `SleepingEvent` | `1` |  |  |
| `StartDay` | `9` |  |  |
| `StarterKit` | `false` |  |  |
| `StartMonth` | `7` |  |  |
| `StartTime` | `2` |  |  |
| `StartYear` | `1` |  |  |
| `StatsDecrease` | `3` |  |  |
| `SurvivalGearsLootNew` | `0.04` |  |  |
| `SurvivorHouseChance` | `2` |  |  |
| `Temperature` | `1` |  |  |
| `TimeSinceApo` | `1` |  |  |
| `ToolLootNew` | `0.04` |  |  |
| `TrafficJam` | `true` |  |  |
| `VehicleEasyUse` | `false` |  |  |
| `VehicleStoryChance` | `2` |  |  |
| `WaterShut` | `1` |  |  |
| `WaterShutModifier` | `-1` |  |  |
| `WeaponLootNew` | `0.04` |  |  |
| `WoundInfectionFactor` | `10.0` |  |  |
| `ZombieAttractionMultiplier` | `10.0` |  |  |
| `ZombieConfig.FollowSoundDistance` | `1000` |  |  |
| `ZombieConfig.PopulationMultiplier` | `4.0` |  |  |
| `ZombieConfig.PopulationPeakDay` | `1` |  |  |
| `ZombieConfig.PopulationPeakMultiplier` | `4.0` |  |  |
| `ZombieConfig.PopulationStartMultiplier` | `4.0` |  |  |
| `ZombieConfig.RallyGroupRadius` | `1` |  |  |
| `ZombieConfig.RallyGroupSeparation` | `5` |  |  |
| `ZombieConfig.RallyGroupSize` | `0` |  |  |
| `ZombieConfig.RallyGroupSizeVariance` | `0` |  |  |
| `ZombieConfig.RallyTravelDistance` | `50` |  |  |
| `ZombieConfig.RedistributeHours` | `1.0` |  |  |
| `ZombieConfig.RespawnHours` | `0.0` |  |  |
| `ZombieConfig.RespawnMultiplier` | `0.0` |  |  |
| `ZombieConfig.RespawnUnseenHours` | `0.0` |  |  |
| `ZombieConfig.ZombiesCountBeforeDelete` | `300` |  |  |
| `ZombieHealthImpact` | `true` |  |  |
| `ZombieLore.ActiveOnly` | `1` |  |  |
| `ZombieLore.ChanceOfAttachedWeapon` | `5` |  |  |
| `ZombieLore.Cognition` | `1` |  |  |
| `ZombieLore.CrawlUnderVehicle` | `7` |  |  |
| `ZombieLore.DisableFakeDead` | `2` |  |  |
| `ZombieLore.DoorOpeningPercentage` | `0` |  |  |
| `ZombieLore.FenceDamageMultiplier` | `1.0` |  |  |
| `ZombieLore.FenceThumpersRequired` | `25` |  |  |
| `ZombieLore.Hearing` | `1` |  |  |
| `ZombieLore.Memory` | `1` |  |  |
| `ZombieLore.Mortality` | `5` |  |  |
| `ZombieLore.PlayerSpawnZombieRemoval` | `4` |  |  |
| `ZombieLore.Reanimate` | `1` |  |  |
| `ZombieLore.Sight` | `1` |  |  |
| `ZombieLore.Speed` | `2` |  |  |
| `ZombieLore.SpottedLogic` | `true` |  |  |
| `ZombieLore.SprinterPercentage` | `0` |  |  |
| `ZombieLore.Strength` | `2` |  |  |
| `ZombieLore.ThumpNoChasing` | `false` |  |  |
| `ZombieLore.ThumpOnConstruction` | `true` |  |  |
| `ZombieLore.Toughness` | `2` |  |  |
| `ZombieLore.Transmission` | `1` |  |  |
| `ZombieLore.TriggerHouseAlarm` | `false` |  |  |
| `ZombieLore.ZombiesArmorFactor` | `2.0` |  |  |
| `ZombieLore.ZombiesCrawlersDragDown` | `true` |  |  |
| `ZombieLore.ZombiesDragDown` | `true` |  |  |
| `ZombieLore.ZombiesFallDamage` | `0.1` |  |  |
| `ZombieLore.ZombiesFenceLunge` | `true` |  |  |
| `ZombieLore.ZombiesMaxDefense` | `85` |  |  |
| `ZombieMigrate` | `true` |  |  |
| `ZombiePopLootEffect` | `10` |  |  |
| `ZombieRespawn` | `4` |  |  |
| `Zombies` | `1` |  |  |
| `ZombieVoronoiNoise` | `true` |  |  |
| `ZoneStoryChance` | `2` |  |  |
