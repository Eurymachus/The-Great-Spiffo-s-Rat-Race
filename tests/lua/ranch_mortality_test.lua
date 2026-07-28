local Mortality = require "TGSRR/Animals/RanchMortality"

local randomCalls = {}
function ZombRand(maximum)
    randomCalls[#randomCalls + 1] = maximum
    return 0
end

local never = {
    Enabled = true,
    RollStartDay = 60,
    FemaleDeathDay = -1,
    MaleDeathDay = -1,
}
assert(Mortality.shouldSpawnDead("female", 10000, never) == false)
assert(Mortality.shouldSpawnDead("male", 10000, never) == false)
assert(#randomCalls == 0)

local vanilla = {
    Enabled = true,
    RollStartDay = 60,
    FemaleDeathDay = 190,
    MaleDeathDay = 250,
}
assert(Mortality.shouldSpawnDead("female", 60, vanilla) == false)
assert(#randomCalls == 0)

assert(Mortality.shouldSpawnDead("female", 61, vanilla) == true)
assert(randomCalls[#randomCalls] == 129)

assert(Mortality.shouldSpawnDead("male", 61, vanilla) == true)
assert(randomCalls[#randomCalls] == 189)

local callsBeforeDeadline = #randomCalls
assert(Mortality.shouldSpawnDead("female", 189, vanilla) == true)
assert(Mortality.shouldSpawnDead("female", 190, vanilla) == true)
assert(#randomCalls == callsBeforeDeadline)

local custom = {
    Enabled = true,
    RollStartDay = 100,
    FemaleDeathDay = 300,
    MaleDeathDay = 400,
}
assert(Mortality.shouldSpawnDead("female", 100, custom) == false)
assert(Mortality.shouldSpawnDead("female", 101, custom) == true)
assert(randomCalls[#randomCalls] == 199)

SandboxVars = {
    TGSRRRanchMortality = {
        Enabled = true,
        RollStartDay = 70,
        FemaleDeathDay = 210,
        MaleDeathDay = -1,
    },
}
local config = Mortality.configuration()
assert(config.rollStartDay == 70)
assert(config.femaleDeathDay == 210)
assert(config.maleDeathDay == -1)

local defaultConfig = Mortality.configuration({})
assert(defaultConfig.enabled == false)
assert(defaultConfig.rollStartDay == 60)
assert(defaultConfig.femaleDeathDay == 190)
assert(defaultConfig.maleDeathDay == 250)

local ignoredOverrides = Mortality.configuration({
    Enabled = false,
    RollStartDay = 0,
    FemaleDeathDay = -1,
    MaleDeathDay = -1,
})
assert(ignoredOverrides.rollStartDay == 60)
assert(ignoredOverrides.femaleDeathDay == 190)
assert(ignoredOverrides.maleDeathDay == 250)

print("ranch mortality test passed")
