local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
local game = "C:/Games/Steam/steamapps/common/ProjectZomboid/media/lua/"
ISBaseTimedAction = {derive = function() return {} end}
package.loaded["TimedActions/ISBaseTimedAction"] = true
for _, name in ipairs({"ISSeedActionNew", "ISHarvestPlantAction"}) do
    assert(loadfile(game .. "shared/Farming/TimedActions/" .. name .. ".lua"))()
    package.loaded["Farming/TimedActions/" .. name] = true
end
function isClient() return false end
function isServer() return false end
function sendRemoveItemFromContainer() end
function sendAddItemsToContainer() end
Perks = {Farming = 1}
local run = {runId = "farming1", lifecycle = "active"}
local recording = true
local inventory = {items = {}}
function inventory:getItems()
    return {size = function() return #self.items end, get = function(_, i) return self.items[i+1] end}
end
function inventory:Remove(item) end
function inventory:AddItems(id, count)
    local result = {}
    for i = 1, count do
        local item = {getFullType = function() return id end}
        self.items[#self.items+1] = item
        result[#result+1] = item
    end
    return result
end
local player = {getInventory = function() return inventory end, getPlayerNum = function() return 0 end,
    getPerkLevel = function() return 1 end, addBackMuscleStrain = function() end}
package.loaded["TGSRR/Run/Recorder"] = {getActiveRun = function() return run end, isActive = function() return recording end}
local plant
SFarmingSystem = {instance = {getLuaObjectAt = function() return plant end, gainXp = function() end,
    growPlant = function() end}}
-- Execute the installed vanilla harvest body with controlled yield and world fixtures.
local file = assert(io.open(game .. "server/Farming/SFarmingSystem.lua")); local source = file:read("*a"); file:close()
local first = assert(source:find("function SFarmingSystem:harvest", 1, true))
local last = assert(source:find("function SFarmingSystem:diseaseThis", first, true))
assert(loadstring(source:sub(first, last-1)))()
SFarmingSystem.instance.harvest = SFarmingSystem.harvest
farming_vegetableconf = {props = {
    Broccoli = {vegetableName = "Base.Broccoli", seedName = "Base.BroccoliSeed", produceExtra = "Base.Hay", growBack = 2},
    Corn = {vegetableName = "Base.Corn", seedName = "Base.Corn"},
}, getSpriteName = function() return nil end}
local yield = 3
function getVegetablesNumber() return yield end
local function fresh(crop)
    plant = {x = 1, y = 2, z = 0, state = "plow", typeOfSeed = crop, owner = 9,
        canHarvest = function(self) return self.hasVegetable == true end,
        seed = function(self, id) self.state = "seeded"; self.typeOfSeed = id end,
        saveData = function() end, harvestThis = function(self) self.state = "harvested" end}
    return plant
end
local Tracker = require("TGSRR/Run/FarmingTracker")
Tracker.initialize(run, player, true)
fresh("Broccoli")
local sow = {character = player, plant = plant, seed = {}, typeOfSeed = "Broccoli"}
ISSeedActionNew.complete(sow); ISSeedActionNew.complete(sow)
assert(run.farming.planted.Broccoli == 1)
ISSeedActionNew.complete({character = player, plant = plant, seed = {}, typeOfSeed = "Broccoli"})
assert(run.farming.planted.Broccoli == 1) -- Seed consumed without planting.
plant.hasVegetable = true; plant.hasSeed = true
local harvest = {character = player, plant = plant}
ISHarvestPlantAction.complete(harvest)
assert(run.farming.harvested.Broccoli == 1 and run.farming.produce["Base.Broccoli"] == 3)
assert(run.farming.produce["Base.Hay"] == 3 and not run.farming.produce["Base.BroccoliSeed"])
ISHarvestPlantAction.complete(harvest)
assert(run.farming.harvested.Broccoli == 1)
plant.hasVegetable = true
ISHarvestPlantAction.complete({character = player, plant = plant})
assert(run.farming.harvested.Broccoli == 2)
fresh("Corn"); plant.hasVegetable = true; plant.hasSeed = true
ISHarvestPlantAction.complete({character = player, plant = plant})
assert(run.farming.produce["Base.Corn"] == 3) -- Excludes same-type seed output.
yield = 0; plant.hasVegetable = true; plant.hasSeed = true
ISHarvestPlantAction.complete({character = player, plant = plant})
assert(run.farming.harvested.Corn == 2 and run.farming.produce["Base.Corn"] == 3)
inventory:AddItems("Base.Corn", 10) -- Looting is not harvesting.
assert(run.farming.produce["Base.Corn"] == 3)
recording = false; fresh("Corn")
ISSeedActionNew.complete({character = player, plant = plant, seed = {}, typeOfSeed = "Corn"})
assert(not run.farming.planted.Corn)
recording = true
Tracker.initialize(run, player, false)
assert(run.farming.harvested.Corn == 2 and not run.farming.partial)
print("vanilla farming sow, yield, seed separation, regrowth and reload checks passed")

-- Cancelled, foreign and failing completions never add observations.
fresh("Corn")
ISSeedActionNew.complete({character = player, plant = plant, seed = {}, typeOfSeed = "Corn", forceStopped = true})
assert(not run.farming.planted.Corn)
fresh("Corn")
local other = setmetatable({}, {__index = player})
ISSeedActionNew.complete({character = other, plant = plant, seed = {}, typeOfSeed = "Corn"})
assert(not run.farming.planted.Corn)
fresh("Corn"); plant.seed = function() error("seed failure") end
assert(not pcall(ISSeedActionNew.complete, {character = player, plant = plant, seed = {}, typeOfSeed = "Corn"}))
assert(not run.farming.planted.Corn)
-- Exercise actual daily snapshot and rollover code with unrelated families stubbed.
for _, name in ipairs({"SkillSnapshot", "WeaponKillSnapshot", "BrokenWeaponSnapshot",
    "AnimalSlaughterSnapshot", "AnimalTrapSnapshot", "AnimalBirthSnapshot",
    "AnimalPetSnapshot", "InjurySnapshot", "MilkSnapshot", "FluidConsumedSnapshot", "FishCaughtSnapshot"}) do
    package.loaded["TGSRR/Run/" .. name] = {
        copy = function() return {} end, totals = function() return {} end,
        deltaPairs = function() return {} end,
    }
end
Events = {EveryDays = {Add = function() end}}

run.lifecycle = "active"
local age = 1
local events = {}
function getGameTime() return {getWorldAgeHours = function() return age end,
    getYear = function() return 1993 end, getMonth = function() return 6 end,
    getDay = function() return age < 24 and 9 or 10 end} end
player.getZombieKills = function() return 0 end
player.getHoursSurvived = function() return age end
package.loaded["TGSRR/Run/Identity"] = {utcSeconds = function() return 100 end}
package.loaded["TGSRR/Run/Recorder"].record = function(kind, payload)
    events[#events+1] = payload
    return true, {utc = 100, worldAgeHours = age}
end
local Daily = require("TGSRR/Run/DailySnapshot")
local Days = require("TGSRR/Run/DayTracker")
assert(Days.initialize(run, player))
fresh("Corn"); plant.hasVegetable = true; yield = 3
ISHarvestPlantAction.complete({character = player, plant = plant})
assert(Daily.active(run, player).farmingProduceDeltas["Base.Corn"] == 3)
age = 25
assert(Days.onNewDay())
assert(events[#events].completedDay.farmingProduceDeltas["Base.Corn"] == 3)
assert(not Daily.active(run, player).farmingProduceDeltas["Base.Corn"])
Tracker.initialize(run, player, false)
assert(run.farming.produce["Base.Corn"] == 6)
fresh("Corn"); plant.hasVegetable = true; yield = 3
ISHarvestPlantAction.complete({character = player, plant = plant})
assert(Daily.active(run, player).farmingProduceDeltas["Base.Corn"] == 3)
assert(run.farming.produce["Base.Corn"] == 9)
print("farming cumulative, daily rollover and reload checks passed")
