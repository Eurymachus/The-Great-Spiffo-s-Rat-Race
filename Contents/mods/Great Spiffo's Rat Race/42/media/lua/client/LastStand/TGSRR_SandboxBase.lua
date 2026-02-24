local TGSRR_SandboxBase = {}

TGSRR_SandboxBase.apply = function()
    SandboxVars.Basement = {
		SpawnFrequency = 7,
	}

	SandboxVars.Map = {
		AllowMiniMap = true,
		AllowWorldMap = true,
		MapAllKnown = true,
		MapNeedsLight = true,
	}

	SandboxVars.ZombieLore = {
		Speed = 2,
		SprinterPercentage = 0,
		Strength = 2,
		Toughness = 2,
		Transmission = 1,
		Mortality = 5,
		Reanimate = 1,
		Cognition = 1,
		CrawlUnderVehicle = 7,
		Memory = 1,
		Sight = 1,
		Hearing = 1,
		SpottedLogic = true,
		ThumpNoChasing = false,
		ThumpOnConstruction = true,
		ActiveOnly = 1,
		TriggerHouseAlarm = false,
		ZombiesDragDown = true,
		ZombiesCrawlersDragDown = true,
		ZombiesFenceLunge = true,
		DisableFakeDead = 2,
		ZombiesArmorFactor = 2.0,
		ZombiesMaxDefense = 85,
		ChanceOfAttachedWeapon = 5,
		ZombiesFallDamage = 0.1,
		PlayerSpawnZombieRemoval = 4,
	}

	SandboxVars.ZombieConfig = {
		PopulationMultiplier = 4.0,
		PopulationStartMultiplier = 4.0,
		PopulationPeakMultiplier = 4.0,
		PopulationPeakDay = 1,
		RespawnHours = 0.0,
		RespawnUnseenHours = 0.0,
		RespawnMultiplier = 0.0,
		RedistributeHours = 1.0,
		FollowSoundDistance = 1000,
		RallyGroupSize = 0,
		RallyGroupSizeVariance = 0,
		RallyTravelDistance = 50,
		RallyGroupSeparation = 5,
		RallyGroupRadius = 1,
		ZombiesCountBeforeDelete = 300,
	}

	SandboxVars.MultiplierConfig = {
		Global = 0.8,
		GlobalToggle = true,
	}

	SandboxVars.Zombies = 1;
	SandboxVars.Distribution = 1;
	SandboxVars.ZombieRespawn = 4;
	SandboxVars.ZombieMigrate = true;
	SandboxVars.DayLength = 3;
	SandboxVars.StartYear = 1;
	SandboxVars.StartMonth = 7;
	SandboxVars.StartDay = 9;
	SandboxVars.StartTime = 2;
	SandboxVars.WaterShut = 1;
	SandboxVars.ElecShut = 1;
	SandboxVars.AlarmDecay = 6;
	SandboxVars.WaterShutModifier = -1;
	SandboxVars.ElecShutModifier = -1;
	--SandboxVars.AlarmDecayModifier = 14;
 	SandboxVars.FoodLootNew = 0.04;
 	SandboxVars.CannedFoodLootNew = 0.04;
 	SandboxVars.LiteratureLootNew = 0.04;
 	SandboxVars.SurvivalGearsLootNew = 0.04;
 	SandboxVars.MedicalLootNew = 0.04;
 	SandboxVars.WeaponLootNew = 0.04;
 	SandboxVars.RangedWeaponLootNew = 0.04;
 	SandboxVars.AmmoLootNew = 0.04;
 	SandboxVars.MechanicsLootNew = 0.04;
 	SandboxVars.OtherLootNew = 0.04;
 	SandboxVars.ClothingLootNew = 0.04;
 	SandboxVars.ContainerLootNew = 0.04;
 	SandboxVars.KeyLootNew = 0.04;
 	SandboxVars.MementoLootNew = 0.04;
 	SandboxVars.MediaLootNew = 0.04;
 	SandboxVars.CookwareLootNew = 0.04;
 	SandboxVars.MaterialLootNew = 0.04;
 	SandboxVars.FarmingLootNew = 0.04;
 	SandboxVars.ToolLootNew = 0.04;

    SandboxVars.LootItemRemovalList = "";
	SandboxVars.RemoveStoryLoot = false;
	SandboxVars.RemoveZombieLoot = false;
	SandboxVars.ZombiePopLootEffect = 10;
	SandboxVars.InsaneLootFactor = 0.05;
	SandboxVars.ExtremeLootFactor = 0.2;
	SandboxVars.RareLootFactor = 0.6;
	SandboxVars.NormalLootFactor = 1.0;
	SandboxVars.CommonLootFactor = 2.0;
	SandboxVars.AbundantLootFactor = 3.0;

	SandboxVars.Temperature = 1;
	SandboxVars.Rain = 1;
	SandboxVars.ErosionSpeed = 4;

	SandboxVars.ErosionDays = 0;

	SandboxVars.ZombieAttractionMultiplier = 10.0;

	SandboxVars.VehicleEasyUse = false;
	SandboxVars.Farming = 3;

	SandboxVars.CompostTime = 8;

	SandboxVars.StatsDecrease = 3;

	SandboxVars.NatureAbundance = 2;
	SandboxVars.FishAbundance = 2;
	SandboxVars.Alarm = 6;
	SandboxVars.LockedHouses = 6;

	SandboxVars.StarterKit = false;
	SandboxVars.Nutrition = true;

	SandboxVars.FoodRotSpeed = 2;
	SandboxVars.FridgeFactor = 2;

	SandboxVars.SeenHoursPreventLootRespawn = 0;
	SandboxVars.HoursForLootRespawn = 0;
	SandboxVars.MaxItemsForLootRespawn = 5;

	SandboxVars.ConstructionPreventsLootRespawn = true;
	SandboxVars.ItemRemovalListBlacklistToggle = false;

	SandboxVars.WorldItemRemovalList = "Base.Hat,Base.Glasses,Base.Maggots,Base.Slug,Base.Slug2,Base.Snail,Base.Worm,Base.Dung_Mouse,Base.Dung_Rat";
	SandboxVars.HoursForWorldItemRemoval = 6.0;
	SandboxVars.TimeSinceApo = 1;
	SandboxVars.PlantResilience = 4;

	SandboxVars.PlantAbundance = 3;
	SandboxVars.EndRegen = 3;
	SandboxVars.Helicopter = 2;

	SandboxVars.MetaEvent = 1;

	SandboxVars.SleepingEvent = 1;

	SandboxVars.GeneratorSpawning = 2;

	SandboxVars.GeneratorFuelConsumption = 1.0;

	SandboxVars.MetaKnowledge = 1;
	SandboxVars.SurvivorHouseChance = 2;
	SandboxVars.VehicleStoryChance = 2;
	SandboxVars.ZoneStoryChance = 2;
	SandboxVars.AnnotatedMapChance = 2;

	SandboxVars.CharacterFreePoints = 0;
	SandboxVars.ConstructionBonusPoints = 3;
	SandboxVars.NightDarkness = 3;
	SandboxVars.NightLength = 3;

	SandboxVars.InjurySeverity = 3;

	SandboxVars.BoneFracture = true;

	SandboxVars.HoursForCorpseRemoval = 120.0;

	SandboxVars.DecayingCorpseHealthImpact = 3;

	SandboxVars.ZombieHealthImpact = true;
	SandboxVars.BloodLevel = 5;
	SandboxVars.ClothingDegradation = 4;

	SandboxVars.FireSpread = true;
	SandboxVars.DaysForRottenFoodRemoval = -1;
	SandboxVars.AllowExteriorGenerator = true;
	SandboxVars.MaxFogIntensity = 1;
	SandboxVars.MaxRainFxIntensity = 1;
	SandboxVars.EnableSnowOnGround = true;
	SandboxVars.MultiHitZombies = false;

	SandboxVars.RearVulnerability = 3;
	SandboxVars.AttackBlockMovements = true;

	SandboxVars.AllClothesUnlocked = false;
	SandboxVars.EnableTaintedWaterText = true;
	SandboxVars.SeeNotLearntRecipe = true;

	SandboxVars.CarSpawnRate = 2;

	SandboxVars.ChanceHasGas = 1;

	SandboxVars.InitialGas = 1;
	SandboxVars.FuelStationGasInfinite = false;
	SandboxVars.FuelStationGasMin = 0.0;
	SandboxVars.FuelStationGasMax = 0.05;
	SandboxVars.FuelStationGasEmptyChance = 25;

	SandboxVars.CarGasConsumption = 1.0;

	SandboxVars.LockedCar = 6;
	SandboxVars.CarGeneralCondition = 1;
	SandboxVars.CarDamageOnImpact = 5;
	SandboxVars.DamageToPlayerFromHitByACar = 5;

	SandboxVars.TrafficJam = true;

	SandboxVars.CarAlarm = 6;

	SandboxVars.PlayerDamageFromCrash = true;

	SandboxVars.SirenShutoffHours = 1.0;
	SandboxVars.RecentlySurvivorVehicles = 1;

	SandboxVars.EnableVehicles = true;
	SandboxVars.SirenEffectsZombies = true;
	SandboxVars.EnablePoisoning = 1;

	SandboxVars.MaggotSpawn = 2;
	SandboxVars.LightBulbLifespan = 10.0;
	SandboxVars.MuscleStrainFactor = 1.67;
	SandboxVars.DiscomfortFactor = 2.0;
	SandboxVars.WoundInfectionFactor = 10.0;

	SandboxVars.NoBlackClothes = true;
	SandboxVars.EasyClimbing = false;
	SandboxVars.MaximumFireFuelHours = 8;
	SandboxVars.AnimalStatsModifier = 4;
	SandboxVars.AnimalMetaStatsModifier = 4;
	SandboxVars.AnimalPregnancyTime = 4;
	SandboxVars.AnimalAgeModifier = 4;
	SandboxVars.AnimalMilkIncModifier = 4;
	SandboxVars.AnimalWoolIncModifier = 4;

	SandboxVars.AnimalRanchChance = 2;
	SandboxVars.AnimalGrassRegrowTime = 720;
	SandboxVars.AnimalMetaPredator = false;
	SandboxVars.AnimalMatingSeason = true;
	SandboxVars.AnimalSoundAttractZombies = true;
	SandboxVars.AnimalEggHatch = 4;

	SandboxVars.MaximumRatIndex = 50;
	SandboxVars.DaysUntilMaximumRatIndex = 90;
	SandboxVars.LevelForDismantleXPCutoff = 0;
	SandboxVars.LevelForMediaXPCutoff = 3;

	SandboxVars.BloodSplatLifespanDays = 3;
	SandboxVars.LiteratureCooldown = 365;

	SandboxVars.NegativeTraitsPenalty = 1;

	SandboxVars.MaximumLooted = 60;
	SandboxVars.DaysUntilMaximumLooted = 3650;
	SandboxVars.RuralLooted = 2.0;
	SandboxVars.MaximumLootedBuildingRooms = 100;
	SandboxVars.MaximumDiminishedLoot = 90;

	SandboxVars.DaysUntilMaximumDiminishedLoot = 3650;
	SandboxVars.MinutesPerPage = 2.0;
	SandboxVars.KillInsideCrops = true;
	SandboxVars.PlantGrowingSeasons = true;
	SandboxVars.PlaceDirtAboveground = false;
	SandboxVars.FarmingSpeedNew = 1.0;
	SandboxVars.FarmingAmountNew = 1.0;
	SandboxVars.FirearmUseDamageChance = true;
	SandboxVars.FirearmNoiseMultiplier = 1.0;
	SandboxVars.FirearmJamMultiplier = 0.0;
	SandboxVars.FirearmMoodleMultiplier = 1.0;
	SandboxVars.FirearmWeatherMultiplier = 1.0;
	SandboxVars.FirearmHeadGearEffect = true;
end

return TGSRR_SandboxBase