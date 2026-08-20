local captured = {}
local current = {
    kills = 10,
    weightKilograms = 80,
    skills = { Fitness = 100, Sprinting = 50 },
    weaponKills = {},
    fireDeaths = 0,
    distanceTravelledMeters = 100,
    brokenWeapons = {},
    animalsSlaughtered = {},
    animalsTrapped = {},
    animalBirths = {},
    animalsPetted = {},
    milkCollected = {},
    butterProduced = 0,
    fishCaught = {},
    injuries = {},
    zombieAssociatedInjuries = {},
    fluidConsumed = {},
    caloriesConsumed = 0,
    generatorRepairs = 0,
    generatorConditionRestored = 0,
    nimbleMovementMilliseconds = 0,
    activeGameplayMilliseconds = 0,
}

package.loaded["TGSRR/Run/Identity"] = {
    utcSeconds = function() return 1000 end,
}
package.loaded["TGSRR/Run/Recorder"] = {
    isActive = function() return true end,
    record = function(eventType, payload, options)
        captured[#captured + 1] = {
            eventType = eventType,
            payload = payload,
        }
        return true, {
            utc = options.utc,
            worldAgeHours = options.worldAgeHours,
        }
    end,
}
package.loaded["TGSRR/Run/DailySnapshot"] = {
    current = function() return current end,
    deltas = function(now, baseline)
        local result = {}
        local keys = {}
        for key in pairs(now or {}) do keys[key] = true end
        for key in pairs(baseline or {}) do keys[key] = true end
        for key in pairs(keys) do
            local delta = (tonumber(now and now[key]) or 0)
                - (tonumber(baseline and baseline[key]) or 0)
            if delta ~= 0 then result[key] = delta end
        end
        return result
    end,
}
package.loaded["TGSRR/Run/AnimalTrapSnapshot"] = {
    deltaPairs = function() return {} end,
}
package.loaded["TGSRR/Run/InjurySnapshot"] = {
    deltaPairs = function() return {} end,
}
package.loaded["TGSRR/Run/TrackingHealth"] = {
    stop = function(reason)
        error("unexpected tracking stop: " .. tostring(reason))
    end,
}

Events = {
    EveryDays = { Add = function() end },
}
function getGameTime()
    return {
        getYear = function() return 1993 end,
        getMonth = function() return 6 end,
        getDay = function() return 12 end,
        getWorldAgeHours = function() return 48 end,
    }
end

local player = {
    getHoursSurvived = function() return 48 end,
}
local run = {
    bootstrapped = false,
    weaponKillsPartial = false,
    fireDeathsPartial = false,
    distanceTravelledPartial = false,
    brokenWeaponsPartial = false,
    animalsSlaughteredPartial = false,
    animalsTrappedPartial = false,
    animalBirthsPartial = false,
    milkCollectedPartial = false,
    butterProducedPartial = false,
    fishCaughtPartial = false,
    injuriesPartial = false,
    animalsPettedPartial = false,
    fluidConsumedPartial = false,
    caloriesConsumedPartial = false,
    generatorRepairsPartial = false,
    nimbleStanceMovementPartial = false,
    activeGameplayPartial = false,
}

local DayTracker = require "TGSRR/Run/DayTracker"
assert(DayTracker.initialize(run, player))
assert(#captured == 1)
assert(captured[1].payload.baseline == nil)
assert(captured[1].payload.previousDay == nil)
assert(captured[1].payload.completedDay == nil)
assert(captured[1].payload.partial == nil)

current = {
    kills = 15,
    weightKilograms = 79.25,
    skills = { Fitness = 125, Sprinting = 50 },
    weaponKills = { ["Base.Axe"] = 5 },
    fireDeaths = 0,
    distanceTravelledMeters = 150,
    brokenWeapons = {},
    animalsSlaughtered = {},
    animalsTrapped = {},
    animalBirths = {},
    animalsPetted = { cow = 2 },
    milkCollected = {},
    butterProduced = 0,
    fishCaught = {},
    injuries = {},
    zombieAssociatedInjuries = {},
    fluidConsumed = { Water = 1.25 },
    caloriesConsumed = 450.5,
    generatorRepairs = 2,
    generatorConditionRestored = 9.5,
    nimbleMovementMilliseconds = 12000,
    activeGameplayMilliseconds = 60000,
}
next = nil -- Match PZ's restricted client Lua globals.
assert(DayTracker.onNewDay())
assert(#captured == 2)
local payload = captured[2].payload
local completed = assert(payload.completedDay)
assert(payload.baseline == nil and payload.previousDay == nil)
assert(completed.dayIndex == 3)
assert(completed.killDelta == 5)
assert(completed.weightDeltaKilograms == -0.75)
assert(completed.xpDeltas.Fitness == 25)
assert(completed.xpDeltas.Sprinting == nil)
assert(completed.weaponKillDeltas["Base.Axe"] == 5)
assert(completed.distanceDeltaMeters == 50)
assert(completed.fireDeathDelta == nil)
assert(completed.brokenWeaponDeltas == nil)
assert(completed.animalPetDeltas.cow == 2)
assert(completed.fluidConsumedDeltas.Water == 1.25)
assert(completed.caloriesConsumedDelta == 450.5)
assert(completed.generatorRepairDelta == 2)
assert(completed.generatorConditionRestoredDelta == 9.5)
assert(completed.nimbleMovementMillisecondsDelta == 12000)
assert(completed.activeGameplayMillisecondsDelta == 60000)
assert(completed.partial == nil)
assert(completed.partialMetrics == nil)

local EventCodec = require "TGSRR/Run/EventCodec"
local canonical = assert(EventCodec.canonicalPayload(payload))
print("compact day test passed; payload bytes=" .. tostring(#canonical))
