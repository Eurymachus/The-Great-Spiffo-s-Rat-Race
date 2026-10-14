package.loaded["TGSRR/Run/Identity"] = { utcSeconds = function() return 100 end }
for _, name in ipairs({"SkillSnapshot", "WeaponKillSnapshot", "BrokenWeaponSnapshot",
    "AnimalSlaughterSnapshot", "AnimalTrapSnapshot", "AnimalBirthSnapshot",
    "AnimalPetSnapshot", "InjurySnapshot", "MilkSnapshot", "FluidConsumedSnapshot",
    "FishCaughtSnapshot"}) do
    package.loaded["TGSRR/Run/" .. name] = {
        copy = function() return {} end,
        totals = function() return {} end,
        deltaPairs = function() return {} end,
    }
end
getGameTime = function() return {getWorldAgeHours = function() return 25 end} end
local measuredWeight = 79.25
local player = {
    getZombieKills = function() return 0 end,
    getNutrition = function() return {getWeight = function() return measuredWeight end} end,
}
local run = {dailyState = {dayIndex = 2, weightKilograms = 80, kills = 0}}
local DailySnapshot = require "TGSRR/Run/DailySnapshot"
local snapshot = DailySnapshot.active(run, player)
assert(snapshot.weightKilograms == 79.25)
assert(snapshot.weightDeltaKilograms == -0.75)
assert(run.dailyState.weightKilograms == 80)
measuredWeight = 80
snapshot = DailySnapshot.active(run, player)
assert(snapshot.weightKilograms == 80)
assert(snapshot.weightDeltaKilograms == 0)
print("daily weight snapshot test passed")
