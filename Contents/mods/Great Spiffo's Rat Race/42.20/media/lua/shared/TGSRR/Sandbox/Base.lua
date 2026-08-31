local TGSRR_SandboxBase = {}

TGSRR_SandboxBase.getSpawnRegions = function()
	local regions = {}

	for _, dir in ipairs(getMapDirectoryTable()) do
		local file = "media/maps/" .. dir .. "/spawnpoints.lua"

		if fileExists(file) then
			table.insert(regions, {
				name = dir,
				file = file,
			})
		end
	end

	return SpawnRegionMgr.loadSpawnRegions(regions)
end

TGSRR_SandboxBase.apply = function()
    SandboxVars.Basement = {

		-- How frequently basements spawn at random locations.
		-- Allowed values:
		--   1 = Never
		--   2 = Extremely Rare
		--   3 = Rare
		--   4 = Sometimes
		--   5 = Often
		--   6 = Very Often
		--   7 = Always
		-- Vanilla default: 4 (Sometimes).
		SpawnFrequency = 7,
	}

	SandboxVars.Map = {

		-- If enabled, a mini-map window will be available.
		-- Vanilla default: false.
		AllowMiniMap = true,

		-- If enabled, the world map can be accessed.
		-- Vanilla default: true.
		AllowWorldMap = true,

		-- If enabled, the world map will be completely filled in on starting the game.
		-- Vanilla default: false.
		MapAllKnown = true,

		-- If enabled, maps can't be read unless there's a source of light available.
		-- Vanilla default: true.
		MapNeedsLight = true,
	}

	SandboxVars.ZombieLore = {

		-- How fast zombies move.
		-- Allowed values:
		--   1 = Sprinters
		--   2 = Fast Shamblers
		--   3 = Shamblers
		--   4 = Random
		-- Vanilla default: 2 (Fast Shamblers).
		Speed = 2,

		-- If Random Speed is enabled, this controls what percentage of zombies are Sprinters. Check the "Advanced" box below to use a custom percentage.
		-- Allowed range: integer 0 to 100.
		-- Vanilla default: 33.
		SprinterPercentage = 0,

		-- The damage zombies inflict per attack.
		-- Allowed values:
		--   1 = Superhuman
		--   2 = Normal
		--   3 = Weak
		--   4 = Random
		-- Vanilla default: 2 (Normal).
		Strength = 2,

		-- The difficulty of killing a zombie.
		-- Allowed values:
		--   1 = Tough
		--   2 = Normal
		--   3 = Fragile
		--   4 = Random
		-- Vanilla default: 2 (Normal).
		Toughness = 2,

		-- How the Knox Virus spreads.
		-- Allowed values:
		--   1 = Blood and Saliva
		--   2 = Saliva Only
		--   3 = Everyone's Infected
		--   4 = None
		-- Vanilla default: 1 (Blood and Saliva).
		Transmission = 1,

		-- How quickly the infection takes effect.
		-- Allowed values:
		--   1 = Instant
		--   2 = 0-30 Seconds
		--   3 = 0-1 Minutes
		--   4 = 0-12 Hours
		--   5 = 2-3 Days
		--   6 = 1-2 Weeks
		--   7 = Never
		-- Vanilla default: 5 (2-3 Days).
		Mortality = 5,

		-- How quickly infected corpses rise as zombies.
		-- Allowed values:
		--   1 = Instant
		--   2 = 0-30 Seconds
		--   3 = 0-1 Minutes
		--   4 = 0-12 Hours
		--   5 = 2-3 Days
		--   6 = 1-2 Weeks
		-- Vanilla default: 3 (0-1 Minutes).
		Reanimate = 1,

		-- Zombie intelligence.
		-- Allowed values:
		--   1 = Navigate and Use Doors
		--   2 = Navigate
		--   3 = Basic Navigation
		--   4 = Random
		-- Vanilla default: 3 (Basic Navigation).
		Cognition = 1,

		-- How often zombies can crawl under parked vehicles.
		-- Allowed values:
		--   1 = Crawlers Only
		--   2 = Extremely Rare
		--   3 = Rare
		--   4 = Sometimes
		--   5 = Often
		--   6 = Very Often
		--   7 = Always
		-- Vanilla default: 5 (Often).
		CrawlUnderVehicle = 7,

		-- How long zombies remember a player after seeing or hearing them.
		-- Allowed values:
		--   1 = Long
		--   2 = Normal
		--   3 = Short
		--   4 = None
		--   5 = Random
		--   6 = Random between Normal and None
		-- Vanilla default: 2 (Normal).
		Memory = 1,

		-- Zombie vision radius.
		-- Allowed values:
		--   1 = Eagle
		--   2 = Normal
		--   3 = Poor
		--   4 = Random
		--   5 = Random between Normal and Poor
		-- Vanilla default: 2 (Normal).
		Sight = 1,

		-- Zombie hearing radius.
		-- Allowed values:
		--   1 = Pinpoint
		--   2 = Normal
		--   3 = Poor
		--   4 = Random
		--   5 = Random between Normal and Poor
		-- Vanilla default: 2 (Normal).
		Hearing = 1,

		-- Activates the new advanced stealth mechanics, which allows you to hide from zombies behind cars, takes traits and weather into account, and much more.
		-- Vanilla default: true.
		SpottedLogic = true,

		-- If zombies that have not seen/heard player can attack doors and constructions while roaming.
		-- Vanilla default: false.
		ThumpNoChasing = false,

		-- If zombies can destroy player constructions and defenses.
		-- Vanilla default: true.
		ThumpOnConstruction = true,

		-- Whether zombies are more "active" during the day or night. "Active" zombies will use the speed set in the "Speed" setting. "Inactive" zombies will be slower, and tend not to give chase.
		-- Allowed values:
		--   1 = Both
		--   2 = Night
		--   3 = Day
		-- Vanilla default: 1 (Both).
		ActiveOnly = 1,

		-- If zombies trigger house alarms when breaking through windows or doors.
		-- Vanilla default: false.
		TriggerHouseAlarm = false,

		-- If multiple attacking zombies can drag you down and kill you. Dependent on zombie strength.
		-- Vanilla default: true.
		ZombiesDragDown = true,

		-- If crawler zombies beside a player contribute to the chance of being dragged down and killed by a group of zombies.
		-- Vanilla default: false.
		ZombiesCrawlersDragDown = true,

		-- If zombies have a chance to lunge at you after climbing over a fence or through a window if you're too close.
		-- Vanilla default: true.
		ZombiesFenceLunge = true,

		-- Whether some dead-looking zombies will reanimate and attack the player.
		-- Allowed values:
		--   1 = World Zombies
		--   2 = World and Combat Zombies
		--   3 = Never
		-- Vanilla default: 1 (World Zombies).
		DisableFakeDead = 2,

		-- Serves as a multiplier when determining the effectiveness of armor worn by zombies.
		-- Allowed range: double 0.0 to 100.0.
		-- Vanilla default: 2.0.
		ZombiesArmorFactor = 2.0,

		-- The maximum defense percentage that any worn protective garments can provide to a zombie.
		-- Allowed range: integer 0 to 100.
		-- Vanilla default: 85.
		ZombiesMaxDefense = 85,

		-- Percentage chance of having a random attached weapon.
		-- Allowed range: integer 0 to 100.
		-- Vanilla default: 6.
		ChanceOfAttachedWeapon = 5,

		-- How much damage zombies take when falling from height.
		-- Allowed range: double 0.0 to 100.0.
		-- Vanilla default: 1.0.
		ZombiesFallDamage = 0.1,

		-- Zombies will not spawn where players spawn.
		-- Allowed values:
		--   1 = Inside the building and around it
		--   2 = Inside the building
		--   3 = Inside the room
		--   4 = Zombies can spawn anywhere
		-- Vanilla default: 1 (Inside the building and around it).
		PlayerSpawnZombieRemoval = 4,

		-- Percentage of eligible zombies that can open doors when door-opening cognition is enabled.
		-- Allowed range: integer 0 to 100.
		-- Vanilla default: 33.
		DoorOpeningPercentage = 0,

		-- How quickly zombies damage tall fences.
		-- Allowed range: double 0.01F to 100.0.
		-- Vanilla default: 1.0.
		FenceDamageMultiplier = 1.0,

		-- How many zombies it takes to damage a tall fence.
		-- Allowed range: integer -1 to 100.
		-- Vanilla default: 50.
		FenceThumpersRequired = 25,
	}

	SandboxVars.ZombieConfig = {

		-- Base multiplier applied to the map's zombie population.
		-- Allowed range: double 0.0 to 4.0.
		-- Vanilla default: 0.65.
		PopulationMultiplier = 4.0,

		-- Population multiplier at world start, before growth toward the peak multiplier.
		-- Allowed range: double 0.0 to 4.0.
		-- Vanilla default: 1.0.
		PopulationStartMultiplier = 4.0,

		-- Target population multiplier reached on the configured peak day.
		-- Allowed range: double 0.0 to 4.0.
		-- Vanilla default: 1.5.
		PopulationPeakMultiplier = 4.0,

		-- World day on which zombie population reaches the configured peak multiplier.
		-- Allowed range: integer 1 to 365.
		-- Vanilla default: 28.
		PopulationPeakDay = 1,

		-- Hours between zombie respawn checks; 0 disables zombie respawn.
		-- Allowed range: double 0.0 to 8760.0.
		-- Vanilla default: 72.0.
		RespawnHours = 0.0,

		-- Hours a chunk must remain unseen before zombies may respawn there.
		-- Allowed range: double 0.0 to 8760.0.
		-- Vanilla default: 16.0.
		RespawnUnseenHours = 0.0,

		-- Fraction of a cell's desired zombie population restored during each respawn cycle.
		-- Allowed range: double 0.0 to 1.0.
		-- Vanilla default: 0.1.
		RespawnMultiplier = 0.0,

		-- Hours between zombie migration and redistribution updates; 0 disables redistribution.
		-- Allowed range: double 0.0 to 8760.0.
		-- Vanilla default: 12.0.
		RedistributeHours = 1.0,

		-- Maximum tile distance zombies will travel while pursuing a sound.
		-- Allowed range: integer 10 to 1000.
		-- Vanilla default: 100.
		FollowSoundDistance = 1000,

		-- Target number of zombies in a rally group; 0 disables rally groups.
		-- Allowed range: integer 0 to 1000.
		-- Vanilla default: 20.
		RallyGroupSize = 0,

		-- Random variation applied above or below the target rally-group size.
		-- Allowed range: integer 0 to 100.
		-- Vanilla default: 50.
		RallyGroupSizeVariance = 0,

		-- Maximum distance zombies travel to join or form a rally group.
		-- Allowed range: integer 5 to 50.
		-- Vanilla default: 20.
		RallyTravelDistance = 50,

		-- Minimum tile spacing maintained between separate rally groups.
		-- Allowed range: integer 5 to 25.
		-- Vanilla default: 15.
		RallyGroupSeparation = 5,

		-- Radius in tiles within which members gather around their rally-group leader.
		-- Allowed range: integer 1 to 10.
		-- Vanilla default: 3.
		RallyGroupRadius = 1,

		-- Agreed Rat Race value: 0.
		-- How many zombies can occupy a certain area before deletion applies.
		-- Allowed range: integer 0 to 5000.
		-- Vanilla default: 300.
		ZombiesCountBeforeDelete = 0,
	}

	SandboxVars.MultiplierConfig = {

		-- The rate at which all skills level up.
		-- Allowed range: double 0.0 to 1000.0.
		-- Vanilla default: 1.0.
		Global = 0.8,

		-- When enabled, all skills will use the Global Multiplier.
		-- Vanilla default: true.
		GlobalToggle = true,

		-- Per-skill XP multipliers; each named entry scales XP earned in that skill.
		-- Allowed range for every entry: 0.0 to 1000.0.
		-- Vanilla default for every entry: 1.0.
		Fitness = 1.0,
		Strength = 1.0,
		Sprinting = 1.0,
		Lightfoot = 1.0,
		Nimble = 1.0,
		Sneak = 1.0,
		Axe = 1.0,
		Blunt = 1.0,
		SmallBlunt = 1.0,
		LongBlade = 1.0,
		SmallBlade = 1.0,
		Spear = 1.0,
		Maintenance = 1.0,
		Farming = 1.0,
		Woodwork = 1.0,
		Carving = 1.0,
		Cooking = 1.0,
		Electricity = 1.0,
		Doctor = 1.0,
		MetalWelding = 1.0,
		Masonry = 1.0,
		Mechanics = 1.0,
		Pottery = 1.0,
		Tailoring = 1.0,
		Aiming = 1.0,
		Reloading = 1.0,
		Fishing = 1.0,
		Trapping = 1.0,
		PlantScavenging = 1.0,
		FlintKnapping = 1.0,
		Husbandry = 1.0,
		Tracking = 1.0,
		Blacksmith = 1.0,
		Butchering = 1.0,
		Glassmaking = 1.0,
	}

	-- Changing this also sets the "Population Multiplier" in Advanced Zombie Options.
	-- Allowed values:
	--   1 = Insane
	--   2 = Very High
	--   3 = High
	--   4 = Normal
	--   5 = Low
	--   6 = None
	-- Vanilla default: 4 (Normal).
	SandboxVars.Zombies = 1;

	-- How zombies are distributed across the map.
	-- Allowed values:
	--   1 = Urban Focused
	--   2 = Uniform
	-- Vanilla default: 1 (Urban Focused).
	SandboxVars.Distribution = 1;

	-- How frequently new zombies are added to the world.
	-- Allowed values:
	--   1 = High
	--   2 = Normal
	--   3 = Low
	--   4 = None
	-- Vanilla default: 2 (Normal).
	SandboxVars.ZombieRespawn = 4;

	-- Zombie allowed to migrate to empty cells.
	-- Vanilla default: true.
	SandboxVars.ZombieMigrate = true;

	-- Selects how much real time one full in-game day lasts.
	-- Values 1 and 2 represent 15 and 30 minutes; 3 represents 1 hour; 4 represents 1 hour 30 minutes.
	-- Values 5 to 26 represent 2 to 23 hours respectively; 27 makes the game clock run in real time.
	-- Vanilla default: 4 (1 Hour, 30 Minutes).
	SandboxVars.DayLength = 4;

	-- Whether the time of day changes naturally, or it's always day/night.
	-- Allowed values:
	--   1 = Normal
	--   2 = Endless Day
	--   3 = Endless Night
	-- Vanilla default: 1 (Normal).
	SandboxVars.DayNightCycle = 1;

	-- Whether weather changes or remains at a single state.
	-- Allowed values:
	--   1 = Normal
	--   2 = No Weather
	--   3 = Endless Rain
	--   4 = Endless Storm
	--   5 = Endless Snow
	--   6 = Endless Blizzard
	-- Vanilla default: 1 (Normal).
	SandboxVars.ClimateCycle = 1;

	-- Whether fog occurs naturally, never occurs, or is always present.
	-- Allowed values:
	--   1 = Normal
	--   2 = No Fog
	--   3 = Endless Fog
	-- Vanilla default: 1 (Normal).
	SandboxVars.FogCycle = 1;

	-- Selects the calendar year in which the game starts.
	-- Allowed range: 1 to 100, representing calendar years 1993 to 2092.
	-- Calendar year = 1992 + configured value.
	-- Vanilla default: 1 (1993).
	SandboxVars.StartYear = 1;

	-- Month in which the game starts.
	-- Allowed values:
	--   1 = January
	--   2 = February
	--   3 = March
	--   4 = April
	--   5 = May
	--   6 = June
	--   7 = July
	--   8 = August
	--   9 = September
	--   10 = October
	--   11 = November
	--   12 = December
	-- Vanilla default: 7 (July).
	SandboxVars.StartMonth = 7;

	-- Selects the calendar day of the month on which the game starts.
	-- Allowed range: 1 to 31, representing the corresponding calendar day.
	-- Vanilla default: 23 (the 23rd).
	SandboxVars.StartDay = 9;

	-- Hour of the day in which the game starts.
	-- Allowed values:
	--   1 = 7 AM
	--   2 = 9 AM
	--   3 = 12 PM
	--   4 = 2 PM
	--   5 = 5 PM
	--   6 = 9 PM
	--   7 = 12 AM
	--   8 = 2 AM
	--   9 = 5 AM
	-- Vanilla default: 2 (9 AM).
	SandboxVars.StartTime = 2;

	-- How long after the default start date (July 9, 1993) that plumbing fixtures (eg. sinks) stop being infinite sources of water.
	-- Allowed values:
	--   1 = Instant
	--   2 = 0 - 30 Days
	--   3 = 0 - 2 Months
	--   4 = 0 - 6 Months
	--   5 = 0 - 1 Year
	--   6 = 0 - 5 Years
	--   7 = 2 - 6 Months
	--   8 = 6 - 12 Months
	--   9 = Disabled
	-- Vanilla default: 2 (0 - 30 Days).
	SandboxVars.WaterShut = 1;

	-- How long after the default start date (July 9, 1993) that the world's electricity turns off for good.
	-- Allowed values:
	--   1 = Instant
	--   2 = 14 - 30 Days
	--   3 = 14 Days - 2 Months
	--   4 = 14 Days - 6 Months
	--   5 = 14 Days - 1 Year
	--   6 = 14 Days - 5 Years
	--   7 = 2 - 6 Months
	--   8 = 6 - 12 Months
	--   9 = Disabled
	-- Vanilla default: 2 (14 - 30 Days).
	SandboxVars.ElecShut = 1;

	-- How long alarm batteries can last for after the power shuts off.
	-- Allowed values:
	--   1 = Instant
	--   2 = 0 - 30 Days
	--   3 = 0 - 2 Months
	--   4 = 0 - 6 Months
	--   5 = 0 - 1 Year
	--   6 = 0 - 5 Years
	-- Vanilla default: 2 (0 - 30 Days).
	-- Safety fallback for any vanilla alarm TGSRR does not claim. TGSRR-owned
	-- alarms use the independent exact range below.
	SandboxVars.AlarmDecay = 5;

	SandboxVars.TGSRRAlarmDecay = {
		-- Lua replacement for vanilla's inaccessible alarm-decay field.
		Enabled = true,
		-- Days after the power shuts off. 730 days is two years.
		MinimumDay = 0,
		MaximumDay = 730,
	}

	-- How long after the default start date (July 9, 1993) that plumbing fixtures (eg. sinks) stop being infinite sources of water.
	-- Allowed range: integer -1 to Integer.MAX_VALUE.
	-- Vanilla default: 14.
	SandboxVars.WaterShutModifier = -1;

	-- How long after the default start date (July 9, 1993) that the world's electricity turns off for good.
	-- Allowed range: integer -1 to Integer.MAX_VALUE.
	-- Vanilla default: 14.
	-- TGSRR keeps the grid online for 72 elapsed hours, then shuts it off at the start of world day 4.
	SandboxVars.ElecShutModifier = 3;

	-- Registered by Build 42.20 but not consumed by its alarm-decay runtime; retained as a legacy preset field.
	-- Allowed range: integer -1 to Integer.MAX_VALUE.
	-- Vanilla default: 14.
	SandboxVars.AlarmDecayModifier = 14;

	-- Any food that can rot or spoil.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.FoodLootNew = 0.04;

	-- Canned and dried food, beverages.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.CannedFoodLootNew = 0.04;

	-- ADDED 42.14
	-- Books that provide skill XP multipliers. Min: 0.00 Max: 4.00 Default: 0.60

	-- Books that provide skill XP multipliers.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
	SandboxVars.SkillBookLoot=0.04
	-- Items that teach recipes. Min: 0.00 Max: 4.00 Default: 0.60

	-- Items that teach recipes.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
	SandboxVars.RecipeResourceLoot=0.04

	-- All other items that can be read, including books, fliers, and newspapers.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
	SandboxVars.LiteratureLootNew = 0.04;

	-- Fishing Rods, Tents, camping gear etc.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.SurvivalGearsLootNew = 0.04;

	-- Medicine, bandages and first aid tools.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.MedicalLootNew = 0.04;

	-- Weapons that are not tools in other categories.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.WeaponLootNew = 0.04;

	-- Also includes weapon attachments.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.RangedWeaponLootNew = 0.04;

	-- Loose ammo, boxes and magazines.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
	SandboxVars.AmmoLootNew = 0.25;

	-- Vehicle parts and the tools needed to install them.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.MechanicsLootNew = 0.04;

	-- Everything else. Also affects foraging for all items in Town/Road zones.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.OtherLootNew = 0.04;

	-- All wearable items that are not containers.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.ClothingLootNew = 0.04;

	-- Backpacks and other wearable/equippable containers, eg. cases.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.ContainerLootNew = 0.04;

	-- Keys for buildings/cars, key rings, and locks.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.KeyLootNew = 0.04;

	-- Spiffo items, plushies, and other collectible keepsake items eg. Photos.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.MementoLootNew = 0.04;

	-- VHS tapes and CDs.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.MediaLootNew = 0.04;

	-- Items that are used in cooking, including those (eg. knives) which can be weapons. Does not include food. Includes both usable and unusable items.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.CookwareLootNew = 0.04;

	-- Items and weapons that are used as ingredients for crafting or building. This is a general category that does not include items belonging to other categories such as Cookware or Medical. Does not include Tools.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.MaterialLootNew = 0.04;

	-- Items and weapons which are used in both animal and plant agriculture, such as Seeds, Trowels, or Shovels.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.FarmingLootNew = 0.04;

	-- Items and weapons which are Tools but don't fit in other categories such as Mechanics or Farming.
	-- Allowed range: double 0.0 to 4.0.
	-- Vanilla default: 0.6.
 	SandboxVars.ToolLootNew = 0.04;

	-- <BHC> [!] It is recommended that you DO NOT change this. [!] <RGB:1,1,1> Can be used to adjust the number of rolls made on loot tables when spawning loot. Will not reduce the number of rolls below 1. Can negatively affect performance if set to high values. It is highly recommended that this not be changed.
	-- Allowed range: double 0.1 to 100.0.
	-- Vanilla default: 1.0.
	SandboxVars.RollsMultiplier = 1.0;

    -- A comma-separated list of item types that won't spawn as ordinary loot.
    -- Allowed value: text.
    -- Vanilla default: "".
    SandboxVars.LootItemRemovalList = "";

	-- If enabled, items on the Loot Item Removal List, or that have their rarity set to 'None', will not spawn in randomised world stories.
	-- Vanilla default: false.
	SandboxVars.RemoveStoryLoot = false;

	-- If enabled, items on the Loot Item Removal List, or that have their rarity set to 'None', will not spawn worn by, or attached to, zombies.
	-- Vanilla default: false.
	SandboxVars.RemoveZombieLoot = false;

	-- If greater than 0, the spawn of loot is increased relative to the number of nearby zombies, with the effect multiplied by this number.
	-- Allowed range: integer 0 to 20.
	-- Vanilla default: 10.
	SandboxVars.ZombiePopLootEffect = 10;

	-- Loot multiplier used when a legacy loot category is set to Insanely Rare.
	-- Allowed range: double 0.0 to 0.2.
	-- Vanilla default: 0.05.
	SandboxVars.InsaneLootFactor = 0.05;

	-- Loot multiplier used when a legacy loot category is set to Extremely Rare.
	-- Allowed range: double 0.05 to 0.6.
	-- Vanilla default: 0.2.
	SandboxVars.ExtremeLootFactor = 0.2;

	-- Loot multiplier used when a legacy loot category is set to Rare.
	-- Allowed range: double 0.2 to 1.0.
	-- Vanilla default: 0.6.
	SandboxVars.RareLootFactor = 0.6;

	-- Loot multiplier used when a legacy loot category is set to Normal.
	-- Allowed range: double 0.6 to 2.0.
	-- Vanilla default: 1.0.
	SandboxVars.NormalLootFactor = 1.0;

	-- Loot multiplier used when a legacy loot category is set to Common.
	-- Allowed range: double 1.0 to 3.0.
	-- Vanilla default: 2.0.
	SandboxVars.CommonLootFactor = 2.0;

	-- Loot multiplier used when a legacy loot category is set to Abundant.
	-- Allowed range: double 2.0 to 4.0.
	-- Vanilla default: 3.0.
	SandboxVars.AbundantLootFactor = 3.0;

	-- The global temperature.
	-- Allowed values:
	--   1 = Very Cold
	--   2 = Cold
	--   3 = Normal
	--   4 = Hot
	--   5 = Very Hot
	-- Vanilla default: 3 (Normal).
	SandboxVars.Temperature = 3;

	-- How often it rains.
	-- Allowed values:
	--   1 = Very Dry
	--   2 = Dry
	--   3 = Normal
	--   4 = Rainy
	--   5 = Very Rainy
	-- Vanilla default: 3 (Normal).
	SandboxVars.Rain = 3;

	-- Number of days until the erosion system (which adds vines, long grass, new trees etc. to the world) will reach 100% growth.
	-- Allowed values:
	--   1 = Very Fast (20 Days)
	--   2 = Fast (50 Days)
	--   3 = Normal (100 Days)
	--   4 = Slow (200 Days)
	--   5 = Very Slow (500 Days)
	-- Vanilla default: 3 (Normal (100 Days)).
	SandboxVars.ErosionSpeed = 4;

	-- For a custom Erosion Speed. Zero means use the Erosion Speed option. Maximum is 36,500 days (approximately 100 years).
	-- Allowed range: integer -1 to 36500.
	-- Vanilla default: 0.
	SandboxVars.ErosionDays = 0;

	-- General engine loudness to zombies.
	-- Allowed range: double 0.0 to 100.0.
	-- Vanilla default: 1.0.
	SandboxVars.ZombieAttractionMultiplier = 5.0;

	-- Whether found vehicles are locked, need keys to start etc.
	-- Vanilla default: false.
	SandboxVars.VehicleEasyUse = false;

	-- The speed of plant growth.
	-- Allowed values:
	--   1 = Very Fast
	--   2 = Fast
	--   3 = Normal
	--   4 = Slow
	--   5 = Very Slow
	-- Vanilla default: 3 (Normal).
	SandboxVars.Farming = 3;

	-- How long it takes for food to break down in a composter.
	-- Allowed values:
	--   1 = 1 Week
	--   2 = 2 Weeks
	--   3 = 3 Weeks
	--   4 = 4 Weeks
	--   5 = 6 Weeks
	--   6 = 8 Weeks
	--   7 = 10 Weeks
	--   8 = 12 Weeks
	-- Vanilla default: 2 (2 Weeks).
	SandboxVars.CompostTime = 8;

	-- How fast the player's hunger, thirst, and fatigue will decrease.
	-- Allowed values:
	--   1 = Very Fast
	--   2 = Fast
	--   3 = Normal
	--   4 = Slow
	--   5 = Very Slow
	-- Vanilla default: 3 (Normal).
	SandboxVars.StatsDecrease = 3;

	-- The abundance of items found in Foraging mode.
	-- Allowed values:
	--   1 = Very Poor
	--   2 = Poor
	--   3 = Normal
	--   4 = Abundant
	--   5 = Very Abundant
	-- Vanilla default: 3 (Normal).
	SandboxVars.NatureAbundance = 2;

	-- The abundance of fish in rivers and lakes.
	-- Allowed values:
	--   1 = Very Poor
	--   2 = Poor
	--   3 = Normal
	--   4 = Abundant
	--   5 = Very Abundant
	-- Vanilla default: 3 (Normal).
	SandboxVars.FishAbundance = 2;

	-- How likely the player is to activate a house alarm when breaking into a new house.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.Alarm = 6;

	-- How frequently the doors of homes and buildings will be locked when discovered.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.LockedHouses = 6;

	-- Spawn with Chips, a Water Bottle, a Small Backpack, a Baseball Bat, and a Hammer.
	-- Vanilla default: false.
	SandboxVars.StarterKit = false;

	-- Nutritional value of food affects the player's condition. Turning this off will stop the player gaining or losing weight.
	-- Vanilla default: false.
	SandboxVars.Nutrition = true;

	-- How fast that food will spoil, inside or outside of a fridge.
	-- Allowed values:
	--   1 = Very Fast
	--   2 = Fast
	--   3 = Normal
	--   4 = Slow
	--   5 = Very Slow
	-- Vanilla default: 3 (Normal).
	SandboxVars.FoodRotSpeed = 2;

	-- How effective a fridge will be at keeping food fresh for longer.
	-- Allowed values:
	--   1 = Very Low
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	--   6 = No decay
	-- Vanilla default: 3 (Normal).
	SandboxVars.FridgeFactor = 2;

	-- When greater than 0, loot will not respawn in zones that have been visited within this number of in-game hours.
	-- Allowed range: integer 0 to Integer.MAX_VALUE.
	-- Vanilla default: 0.
	SandboxVars.SeenHoursPreventLootRespawn = 0;

	-- When greater than 0, after X hours, all containers in towns and trailer parks in the world will respawn loot. To spawn loot a container must have been looted at least once. Loot respawn is not impacted by visibility or subsequent looting.
	-- Allowed range: integer 0 to Integer.MAX_VALUE.
	-- Vanilla default: 0.
	SandboxVars.HoursForLootRespawn = 0;

	-- Containers with a number of items greater, or equal to, this setting will not respawn.
	-- Allowed range: integer 0 to Integer.MAX_VALUE.
	-- Vanilla default: 5.
	SandboxVars.MaxItemsForLootRespawn = 5;

	-- Items will not respawn in buildings that players have barricaded or built in.
	-- Vanilla default: true.
	SandboxVars.ConstructionPreventsLootRespawn = true;

	-- If true, any items *not* in WorldItemRemovalList will be removed.
	-- Vanilla default: false.
	SandboxVars.ItemRemovalListBlacklistToggle = false;

	-- A comma-separated list of item types that will be removed after HoursForWorldItemRemoval hours.
	-- Allowed value: text.
	-- Vanilla default: "Base.Hat, Base.Glasses, Base.Dung_Turkey, Base.Dung_Chicken, Base.Dung_Cow, Base.Dung_Deer, Base.Dung_Mouse, Base.Dung_Pig, Base.Dung_Rabbit, Base.Dung_Rat, Base.Dung_Sheep".
	SandboxVars.WorldItemRemovalList = "Base.Hat,Base.Glasses,Base.Maggots,Base.Slug,Base.Slug2,Base.Snail,Base.Worm,Base.Dung_Mouse,Base.Dung_Rat";

	-- Number of hours since an item was dropped on the ground before it is removed. Items are removed the next time that part of the map is loaded. Zero means items are not removed.
	-- Allowed range: double 0.0 to 2.147483647E9.
	-- Vanilla default: 24.0.
	SandboxVars.HoursForWorldItemRemoval = 6.0;

	-- How long after the end of the world to begin. This will affect starting world erosion and food spoilage. Does not affect the starting date.
	-- Allowed values:
	--   1 = 0
	--   2 = 1
	--   3 = 2
	--   4 = 3
	--   5 = 4
	--   6 = 5
	--   7 = 6
	--   8 = 7
	--   9 = 8
	--   10 = 9
	--   11 = 10
	--   12 = 11
	--   13 = 12
	-- Vanilla default: 1 (0).
	SandboxVars.TimeSinceApo = 1;

	-- How much water plants will lose per day, and their ability to avoid disease.
	-- Allowed values:
	--   1 = Very High
	--   2 = High
	--   3 = Normal
	--   4 = Low
	--   5 = Very Low
	-- Vanilla default: 3 (Normal).
	SandboxVars.PlantResilience = 4;

	-- The yield of plants when harvested.
	-- Allowed values:
	--   1 = Very Poor
	--   2 = Poor
	--   3 = Normal
	--   4 = Abundant
	--   5 = Very Abundant
	-- Vanilla default: 3 (Normal).
	SandboxVars.PlantAbundance = 3;

	-- Recovery from being tired after performing actions.
	-- Allowed values:
	--   1 = Very Fast
	--   2 = Fast
	--   3 = Normal
	--   4 = Slow
	--   5 = Very Slow
	-- Vanilla default: 3 (Normal).
	SandboxVars.EndRegen = 3;

	-- How regularly a helicopter passes over the Event Zone.
	-- Allowed values:
	--   1 = Never
	--   2 = Once
	--   3 = Sometimes
	--   4 = Often
	-- Vanilla default: 2 (Once).
	SandboxVars.Helicopter = 1;
	SandboxVars.TGSRRHelicopter = {

		-- Replaces vanilla helicopter recurrence with this schedule. The vanilla helicopter event itself is retained.
		-- TGSRR option with no vanilla counterpart. Registration default: false.
		Enabled = true,

		-- Each listed month receives one event slot anchored to the challenge's original start day-of-month. For the default July 9 start, every slot is anchored to the 9th.
		-- Comma-separated calendar month numbers only, for example 7,1 for July and January. Leave empty for no custom events in this challenge year.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year1Months = "7",

		-- Comma-separated calendar month numbers only, for example 7,1 for July and January. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year2Months = "7,1",

		-- Comma-separated calendar month numbers only, for example 7,11,3. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year3Months = "7,11,3",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year4Months = "7,10,1,4",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year5Months = "7,9,11,1,3",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year6Months = "7,10,1,4",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year7Months = "7,11,3",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year8Months = "7,1",

		-- Comma-separated calendar month numbers only. Leave empty for no custom events.
		-- Allowed value: text.
		-- TGSRR option with no vanilla counterpart. Registration default: "".
		Year9Months = "7",

		-- Minimum world-day delay from the challenge start day within each scheduled month slot. With the July 9 challenge start and the default value 6, the earliest event date is the 15th.
		-- Allowed range: integer 0 to 31.
		-- TGSRR option with no vanilla counterpart. Registration default: 6.
		DayMinimum = 6,

		-- Exclusive maximum world-day delay from the challenge start day within each scheduled month slot. The default range 6 to 10 matches vanilla Rand.Next(6, 10), producing delays 6, 7, 8, or 9 and dates from the 15th through 18th.
		-- Allowed range: integer 1 to 32.
		-- TGSRR option with no vanilla counterpart. Registration default: 10.
		DayMaximum = 10,

		-- Earliest hour of day that may be selected for a scheduled helicopter event.
		-- Allowed range: integer 0 to 23.
		-- TGSRR option with no vanilla counterpart. Registration default: 9.
		StartHourMinimum = 9,

		-- Latest hour of day that may be selected for a scheduled helicopter event.
		-- Allowed range: integer 0 to 23.
		-- TGSRR option with no vanilla counterpart. Registration default: 18.
		StartHourMaximum = 18,

		-- Minimum length in hours of the activation-opportunity window. This does not control the helicopter's flight duration.
		-- Allowed range: integer 1 to 24.
		-- TGSRR option with no vanilla counterpart. Registration default: 1.
		DurationMinimum = 1,

		-- Maximum length in hours of the activation-opportunity window. This does not control the helicopter's flight duration.
		-- Allowed range: integer 1 to 24.
		-- TGSRR option with no vanilla counterpart. Registration default: 4.
		DurationMaximum = 4,
	};

	-- How often zombie-attracting metagame events like distant gunshots will occur.
	-- Allowed values:
	--   1 = Never
	--   2 = Sometimes
	--   3 = Often
	-- Vanilla default: 2 (Sometimes).
	SandboxVars.MetaEvent = 1;

	-- How often events during the player's sleep, like nightmares, occur.
	-- Allowed values:
	--   1 = Never
	--   2 = Sometimes
	--   3 = Often
	-- Vanilla default: 1 (Never).
	SandboxVars.SleepingEvent = 1;

	-- The chance of electrical generators spawning on the map.
	-- Allowed values:
	--   1 = None (not recommended)
	--   2 = Insanely Rare
	--   3 = Extremely Rare
	--   4 = Rare
	--   5 = Normal
	--   6 = Common
	--   7 = Abundant
	-- Vanilla default: 5 (Normal).
	SandboxVars.GeneratorSpawning = 2;

	-- How much fuel is consumed by generators per in-game hour.
	-- Allowed range: double 0.0 to 100.0.
	-- Vanilla default: 0.1.
	SandboxVars.GeneratorFuelConsumption = 0.1; -- Pre B42.12 was 1.0

	-- Horizontal tile radius within which a generator can supply electrical power.
	-- Allowed range: integer 1 to 100.
	-- Vanilla default: 20.
	SandboxVars.GeneratorTileRange = 20;

	-- How many levels both above and below a generator it can provide with electricity.
	-- Allowed range: integer 1 to 15.
	-- Vanilla default: 3.
	SandboxVars.GeneratorVerticalPowerRange = 3;

	-- If a piece of media hasn't been fully seen or read, this setting determines whether it's displayed fully, displayed as "???", or hidden completely.
	-- Allowed values:
	--   1 = Fully revealed
	--   2 = Shown as ???
	--   3 = Completely hidden
	-- Vanilla default: 3 (Completely hidden).
	SandboxVars.MetaKnowledge = 1;

	-- The chance of finding randomized buildings on the map (eg. burnt out houses, ones containing loot stashes or dead bodies).
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	--   7 = Always Tries
	-- Vanilla default: 3 (Rare).
	SandboxVars.SurvivorHouseChance = 2;

	-- The chance of road stories (eg. police roadblocks) spawning.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	--   7 = Always Tries
	-- Vanilla default: 3 (Rare).
	SandboxVars.VehicleStoryChance = 2;

	-- The chance of stories specific to map zones (eg. a campsite in a forest) spawning.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	--   7 = Always Tries
	-- Vanilla default: 3 (Rare).
	SandboxVars.ZoneStoryChance = 2;

	-- How often a looted map will have notes on it, written by a deceased survivor.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.AnnotatedMapChance = 2;

	-- Adds free points during character creation.
	-- Allowed range: integer -100 to 100.
	-- Vanilla default: 0.
	SandboxVars.CharacterFreePoints = 0;

	-- Gives player-built constructions extra hit points so they are more resistant to zombie damage.
	-- Allowed values:
	--   1 = Very Low
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	-- Vanilla default: 3 (Normal).
	SandboxVars.ConstructionBonusPoints = 3;

	-- The level of ambient lighting at night.
	-- Allowed values:
	--   1 = Pitch Black
	--   2 = Dark
	--   3 = Normal
	--   4 = Bright
	-- Vanilla default: 3 (Normal).
	SandboxVars.NightDarkness = 3;

	-- The time from dusk to dawn.
	-- Allowed values:
	--   1 = Always Night
	--   2 = Long
	--   3 = Normal
	--   4 = Short
	--   5 = Always Day
	-- Vanilla default: 3 (Normal).
	SandboxVars.NightLength = 3;

	-- The impact that injuries have on your body, and their healing time.
	-- Allowed values:
	--   1 = Low
	--   2 = Normal
	--   3 = High
	-- Vanilla default: 2 (Normal).
	SandboxVars.InjurySeverity = 3;

	-- If survivors can get broken limbs from impacts, zombie damage, falls etc.
	-- Vanilla default: true.
	SandboxVars.BoneFracture = true;

	-- How long, in hours, before dead zombie bodies disappear from the world. If 0, maggots will not spawn on corpses.
	-- Allowed range: double -1.0 to 2.147483647E9.
	-- Vanilla default: -1.0.
	SandboxVars.HoursForCorpseRemoval = 120.0;

	-- The impact that nearby decaying bodies has on the player's health and emotions.
	-- Allowed values:
	--   1 = None
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Insane
	-- Vanilla default: 3 (Normal).
	SandboxVars.DecayingCorpseHealthImpact = 3;

	-- Whether nearby "living" zombies have the same impact on the player's health and emotions.
	-- Vanilla default: false.
	SandboxVars.ZombieHealthImpact = true;

	-- How much blood is sprayed on floors and walls by injuries.
	-- Allowed values:
	--   1 = None
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Ultra Gore
	-- Vanilla default: 3 (Normal).
	SandboxVars.BloodLevel = 5;

	-- How quickly clothing degrades, becomes dirty, and bloodied.
	-- Allowed values:
	--   1 = Disabled
	--   2 = Slow
	--   3 = Normal
	--   4 = Fast
	-- Vanilla default: 3 (Normal).
	SandboxVars.ClothingDegradation = 4;

	-- If fires spread when started.
	-- Vanilla default: true.
	SandboxVars.FireSpread = true;

	-- Number of in-game days before rotten food is removed from the map. -1 means rotten food is never removed.
	-- Allowed range: integer -1 to Integer.MAX_VALUE.
	-- Vanilla default: -1.
	SandboxVars.DaysForRottenFoodRemoval = -1;

	-- If enabled, generators will work on exterior tiles. This will allow, for example, the powering of gas pumps.
	-- Vanilla default: true.
	SandboxVars.AllowExteriorGenerator = true;

	-- Maximum intensity of fog.
	-- Allowed values:
	--   1 = Normal
	--   2 = Moderate
	--   3 = Low
	--   4 = None
	-- Vanilla default: 1 (Normal).
	SandboxVars.MaxFogIntensity = 1;

	-- Maximum intensity of rain.
	-- Allowed values:
	--   1 = Normal
	--   2 = Moderate
	--   3 = Low
	-- Vanilla default: 1 (Normal).
	SandboxVars.MaxRainFxIntensity = 1;

	-- If snow will accumulate on the ground. If disabled, snow will still show on vegetation and rooftops.
	-- Vanilla default: true.
	SandboxVars.EnableSnowOnGround = true;

	-- If certain melee weapons will be able to strike multiple zombies in one hit.
	-- Vanilla default: false.
	SandboxVars.MultiHitZombies = false;

	-- Chance of being bitten when a zombie attacks from behind.
	-- Allowed values:
	--   1 = Low
	--   2 = Medium
	--   3 = High
	-- Vanilla default: 3 (High).
	SandboxVars.RearVulnerability = 3;

	-- If melee attacking slows you down.
	-- Vanilla default: true.
	SandboxVars.AttackBlockMovements = true;

	-- Allows you to select from every piece of clothing in the game when customizing your character
	-- Vanilla default: false.
	SandboxVars.AllClothesUnlocked = false;

	-- If tainted water will show a warning marking it as such.
	-- Vanilla default: true.
	SandboxVars.EnableTaintedWaterText = true;

	-- If true, you will be able to see any recipes that can be done with a station, even if you haven't learnt them yet.
	-- Vanilla default: true.
	SandboxVars.SeeNotLearntRecipe = true;

	-- How frequently vehicles can be discovered on the map.
	-- Allowed values:
	--   1 = None
	--   2 = Very Low
	--   3 = Low
	--   4 = Normal
	--   5 = High
	-- Vanilla default: 4 (Normal).
	SandboxVars.CarSpawnRate = 2;

	-- The chance of finding a vehicle with gas in its tank.
	-- Allowed values:
	--   1 = Low
	--   2 = Normal
	--   3 = High
	-- Vanilla default: 2 (Normal).
	SandboxVars.ChanceHasGas = 1;

	-- How full the gas tank of discovered vehicles will be.
	-- Allowed values:
	--   1 = Very Low
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	--   6 = Full
	-- Vanilla default: 3 (Normal).
	SandboxVars.InitialGas = 1;

	-- If enabled, gas pumps will never run out of fuel
	-- Vanilla default: false.
	SandboxVars.FuelStationGasInfinite = false;

	-- The minimum amount of gasoline that can spawn in gas pumps. Check the "Advanced" box below to use a custom amount.
	-- Allowed range: double 0.0 to 1.0.
	-- Vanilla default: 0.0.
	SandboxVars.FuelStationGasMin = 0.0;

	-- The maximum amount of gasoline that can spawn in gas pumps. Check the "Advanced" box below to use a custom amount.
	-- Allowed range: double 0.0 to 1.0.
	-- Vanilla default: 0.7.
	SandboxVars.FuelStationGasMax = 0.05;

	-- The chance, as a percentage, that individual gas pumps will initially have no fuel.
	-- Allowed range: integer 0 to 100.
	-- Vanilla default: 20.
	SandboxVars.FuelStationGasEmptyChance = 25;

	-- How gas-hungry vehicles are.
	-- Allowed range: double 0.0 to 100.0.
	-- Vanilla default: 1.0.
	SandboxVars.CarGasConsumption = 1.0;

	-- How likely cars will be locked
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.LockedCar = 6;

	-- General condition discovered vehicles will be in.
	-- Allowed values:
	--   1 = Very Low
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	-- Vanilla default: 3 (Normal).
	SandboxVars.CarGeneralCondition = 1;

	-- The amount of damage dealt to vehicles that crash.
	-- Allowed values:
	--   1 = Very Low
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	-- Vanilla default: 3 (Normal).
	SandboxVars.CarDamageOnImpact = 5;

	-- Damage received by the player from being crashed into.
	-- Allowed values:
	--   1 = None
	--   2 = Low
	--   3 = Normal
	--   4 = High
	--   5 = Very High
	-- Vanilla default: 1 (None).
	SandboxVars.DamageToPlayerFromHitByACar = 5;

	-- If traffic jams consisting of wrecked cars will appear on main roads.
	-- Vanilla default: true.
	SandboxVars.TrafficJam = true;

	-- How frequently discovered vehicles have active alarms.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.CarAlarm = 6;

	-- If the player can get injured from being in a car accident.
	-- Vanilla default: true.
	SandboxVars.PlayerDamageFromCrash = true;

	-- How many in-game hours before a wailing siren shuts off.
	-- Allowed range: double 0.0 to 168.0.
	-- Vanilla default: 0.0.
	SandboxVars.SirenShutoffHours = 1.0;

	-- Whether a player can discover a car that has been cared for after the Knox infection struck.
	-- Allowed values:
	--   1 = None
	--   2 = Low
	--   3 = Normal
	--   4 = High
	-- Vanilla default: 3 (Normal).
	SandboxVars.RecentlySurvivorVehicles = 1;

	-- If vehicles will spawn.
	-- Vanilla default: true.
	SandboxVars.EnableVehicles = true;

	-- If zombies will head towards the sound of vehicle sirens.
	-- Vanilla default: true.
	SandboxVars.SirenEffectsZombies = true;

	-- If poison can be added to food.
	-- Allowed values:
	--   1 = True
	--   2 = False
	--   3 = Only bleach poisoning is disabled
	-- Vanilla default: 1 (True).
	SandboxVars.EnablePoisoning = 1;

	-- If/when maggots can spawn in corpses.
	-- Allowed values:
	--   1 = In and Around Bodies
	--   2 = In Bodies Only
	--   3 = Never
	-- Vanilla default: 1 (In and Around Bodies).
	SandboxVars.MaggotSpawn = 2;

	-- The higher the value, the longer lightbulbs last before breaking. If 0, lightbulbs will never break. Does not affect vehicle headlights.
	-- Allowed range: double 0.0 to 1000.0.
	-- Vanilla default: 1.0.
	SandboxVars.LightBulbLifespan = 30.0;

	-- Functions as a multiplier when applying muscle strain from swinging weapons or carrying heavy loads.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 1.0.
	SandboxVars.MuscleStrainFactor = 1.67;

	-- Functions as a multiplier when applying discomfort from worn items.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 1.0.
	SandboxVars.DiscomfortFactor = 2.0;

	-- If greater than zero damage can be taken from serious wound infections.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 0.0.
	SandboxVars.WoundInfectionFactor = 10.0;

	-- If true clothing with randomized tints will not be so dark to be virtually black.
	-- Vanilla default: true.
	SandboxVars.NoBlackClothes = true;

	-- Disables the failure chances when climbing sheet ropes or over walls.
	-- Vanilla default: false.
	SandboxVars.EasyClimbing = false;

	-- The maximum hours of fuel that can be placed in a campfire, wood stove etc.
	-- Allowed range: integer 1 to 168.
	-- Vanilla default: 8.
	SandboxVars.MaximumFireFuelHours = 12;

	-- Speed at which animals stats (hunger, thirst etc.) reduce.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 4 (Normal).
	SandboxVars.AnimalStatsModifier = 4;

	-- Speed at which animals stats (hunger, thirst etc.) reduce while in meta.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 4 (Normal).
	SandboxVars.AnimalMetaStatsModifier = 4;

	-- How long animals will be pregnant for before giving birth.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 2 (Very Fast).
	SandboxVars.AnimalPregnancyTime = 4;

	-- Speed at which animals age.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 3 (Fast).
	SandboxVars.AnimalAgeModifier = 4;

	-- Multiplier controlling how quickly milk replenishes in milk-producing animals.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 3 (Fast).
	SandboxVars.AnimalMilkIncModifier = 4;

	-- Multiplier controlling how quickly wool regrows on wool-producing animals.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 3 (Fast).
	SandboxVars.AnimalWoolIncModifier = 4;

	-- The chance of finding animals in farm.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	--   7 = Always
	-- Vanilla default: 7 (Always).
	SandboxVars.AnimalRanchChance = 2;

	-- The number of hours grass will regrow after being eaten by an animal or cut by the player.
	-- Allowed range: integer 1 to 9999.
	-- Vanilla default: 240.
	SandboxVars.AnimalGrassRegrowTime = 720;

	-- If a meta (ie. not actually visible in-game) fox may attack your chickens if the hutch's door is left open at night.
	-- Vanilla default: false.
	SandboxVars.AnimalMetaPredator = false;

	-- If on, animals will only mate during their breeding season (if any). Otherwise they can reproduce/lay eggs all year round.
	-- Vanilla default: true.
	SandboxVars.AnimalMatingSeason = true;

	-- If true, animal calls will attract nearby zombies.
	-- Vanilla default: false.
	SandboxVars.AnimalSoundAttractZombies = true;

	-- How long before baby animals will hatch from eggs.
	-- Allowed values:
	--   1 = Ultra Fast
	--   2 = Very Fast
	--   3 = Fast
	--   4 = Normal
	--   5 = Slow
	--   6 = Very Slow
	-- Vanilla default: 3 (Fast).
	SandboxVars.AnimalEggHatch = 4;

	-- The chance of animals leaving tracks.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.AnimalTrackChance = 4;

	-- The chance of creating a path for animals to be hunted.
	-- Allowed values:
	--   1 = Never
	--   2 = Extremely Rare
	--   3 = Rare
	--   4 = Sometimes
	--   5 = Often
	--   6 = Very Often
	-- Vanilla default: 4 (Sometimes).
	SandboxVars.AnimalPathChance = 4;
	SandboxVars.TGSRRRanchMortality = {

		-- When disabled, ranch spawning uses vanilla's day 60 mortality start, day 190 female deadline, and day 250 male deadline.
		-- TGSRR option with no vanilla counterpart. Registration default: false.
		Enabled = true,

		-- Used only when custom ranch mortality is enabled. Ranch animals spawned on or before this elapsed world day are always alive. Vanilla uses day 60.
		-- Allowed range: integer 0 to 10000.
		-- TGSRR option with no vanilla counterpart. Registration default: 60.
		RollStartDay = 60,

		-- Used only when custom ranch mortality is enabled. Female ranch animals use vanilla's increasing mortality roll and are guaranteed dead by this day. Use -1 to disable female mortality.
		-- Allowed range: integer -1 to 10000.
		-- TGSRR option with no vanilla counterpart. Registration default: 190.
		FemaleDeathDay = -1,

		-- Used only when custom ranch mortality is enabled. Male ranch animals use vanilla's increasing mortality roll and are guaranteed dead by this day. Use -1 to disable male mortality.
		-- Allowed range: integer -1 to 10000.
		-- TGSRR option with no vanilla counterpart. Registration default: 250.
		MaleDeathDay = -1,
	};

	-- The frequency and intensity of eg. rats in infested buildings.
	-- Allowed range: integer 0 to 50.
	-- Vanilla default: 25.
	SandboxVars.MaximumRatIndex = 50;

	-- How long it takes for the Maximum Vermin Index to be reached.
	-- Allowed range: integer 0 to 365.
	-- Vanilla default: 90.
	SandboxVars.DaysUntilMaximumRatIndex = 90;

	-- When a skill is at this level or above, scrapping furniture does not provide XP for the relevant skill. Does not apply to Electrical.
	-- Allowed range: integer 0 to 10.
	-- Vanilla default: 0.
	SandboxVars.LevelForDismantleXPCutoff = 0;

	-- When a skill is at this level or above, television/VHS/other media will not provide XP for it.
	-- Allowed range: integer 0 to 10.
	-- Vanilla default: 3.
	SandboxVars.LevelForMediaXPCutoff = 3;

	-- Number of days before old blood splats are removed. Removal happens when map chunks are loaded. 0 means they will never disappear.
	-- Allowed range: integer 0 to 365.
	-- Vanilla default: 0.
	SandboxVars.BloodSplatLifespanDays = 3;

	-- Number of days before one can benefit from reading previously read literature items.
	-- Allowed range: integer 1 to 365.
	-- Vanilla default: 90.
	SandboxVars.LiteratureCooldown = 365;

	-- If there are diminishing returns on bonus trait points provided from selecting multiple negative traits.
	-- Allowed values:
	--   1 = None
	--   2 = 1 point penalty for every 3 negative traits selected
	--   3 = 1 point penalty for every 2 negative traits selected
	--   4 = 1 point penalty for every negative trait selected after the first
	-- Vanilla default: 1 (None).
	SandboxVars.NegativeTraitsPenalty = 1;

	-- The chance that any building will already be looted when found. Check the "Advanced" box below to use a custom number.
	-- Allowed range: integer 0 to 200.
	-- Vanilla default: 50.
	SandboxVars.MaximumLooted = 60;

	-- How long it takes for Maximum Looted Building Chance to be reached.
	-- Allowed range: integer 0 to 3650.
	-- Vanilla default: 90.
	SandboxVars.DaysUntilMaximumLooted = 3650;

	-- The chance that any rural building will already be looted when found. Check the "Advanced" box below to use a custom number.
	-- Allowed range: double 0.0 to 2.0.
	-- Vanilla default: 0.5.
	SandboxVars.RuralLooted = 2.0;

	-- If a building has more than this amount of rooms it will not be looted.
	-- Allowed range: integer 0 to 200.
	-- Vanilla default: 50.
	SandboxVars.MaximumLootedBuildingRooms = 100;

	-- The maximum loot that won't spawn when Days Until Maximum Diminished Loot is reached. Check the "Advanced" box below to use an exact percentage.
	-- Allowed range: integer 0 to 100.
	-- Vanilla default: 0.
	SandboxVars.MaximumDiminishedLoot = 0;

	-- How long it takes for Maximum Diminished Loot Percentage to be reached.
	-- Allowed range: integer 0 to 3650.
	-- Vanilla default: 3650.
	SandboxVars.DaysUntilMaximumDiminishedLoot = 1825;

	-- The number of in-game minutes it takes to read one page of a skill book.
	-- Allowed range: double 0.0 to 60.0.
	-- Vanilla default: 2.0.
	SandboxVars.MinutesPerPage = 2.0;

	-- When enabled, crops and herbs grown inside buildings will die. Does not affect houseplants.
	-- Vanilla default: true.
	SandboxVars.KillInsideCrops = true;

	-- When enabled, the growth of plants is affected by seasons.
	-- Vanilla default: true.
	SandboxVars.PlantGrowingSeasons = true;

	-- <BHC> [!] It is recommended that you DO NOT change this. Changing this can result in performance issues. [!] <RGB:1,1,1> When enabled, dirt can be placed, and farming performed on other than the ground level.
	-- Vanilla default: false.
	SandboxVars.PlaceDirtAboveground = false;

	-- The speed of plant growth.
	-- Allowed range: double 0.1 to 100.0.
	-- Vanilla default: 1.0.
	SandboxVars.FarmingSpeedNew = 1.0;

	-- The abundance of harvested crops.
	-- Allowed range: double 0.1 to 10.0.
	-- Vanilla default: 1.0.
	SandboxVars.FarmingAmountNew = 1.0;

	-- Replaces Chance-To-Hit mechanics with Chance-To-Damage calculations. This mode prioritizes player aiming.
	-- Allowed values:
	--   1 = Disabled
	--   2 = Zombies only
	--   3 = All types of target
	-- Vanilla default: 2 (Zombies only).
	SandboxVars.FirearmUseDamageChance = 2;

	-- A multiplier for the distance at which zombies can hear gunshots.
	-- Allowed range: double 0.2 to 2.0.
	-- Vanilla default: 1.0.
	SandboxVars.FirearmNoiseMultiplier = 1.0;

	-- Multiplier for firearm jamming chance. 0 disables jamming.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 0.0.
	SandboxVars.FirearmJamMultiplier = 0.0;

	-- Multiplier for Moodle effects on hit chance. 0 disables Moodle penalty.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 1.0.
	SandboxVars.FirearmMoodleMultiplier = 1.0;

	-- Multiplier for the effects of weather (wind, rain and fog) on hit chance. 0 disables weather effect.
	-- Allowed range: double 0.0 to 10.0.
	-- Vanilla default: 1.0.
	SandboxVars.FirearmWeatherMultiplier = 1.0;

	-- Enable to have headgear like welding masks affect hit chance
	-- Vanilla default: true.
	SandboxVars.FirearmHeadGearEffect = true;

	-- Chance to turn a dirt floor into a clay floor. Applies to lakes.
	-- Allowed range: double 0.0 to 1.0.
	-- Vanilla default: 0.05.
	SandboxVars.ClayLakeChance = 0.05;

	-- Chance to turn a dirt floor into a clay floor. Applies to rivers.
	-- Allowed range: double 0.0 to 1.0.
	-- Vanilla default: 0.05.
	SandboxVars.ClayRiverChance = 0.05;

	-- Adds Voronoi-noise variation to zombie distribution so density is less spatially uniform.
	-- Vanilla default: true.
	SandboxVars.ZombieVoronoiNoise = true;

	-- Close the player-facing tracker windows when vanilla Search Mode detects zombie danger.
	SandboxVars.TGSRRTracker = {
		DangerAutoClose = true,
	};
end

return TGSRR_SandboxBase
