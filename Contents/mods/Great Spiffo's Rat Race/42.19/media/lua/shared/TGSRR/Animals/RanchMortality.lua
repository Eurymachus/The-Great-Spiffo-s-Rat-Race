local Mortality = {}

Mortality.DEFAULT_ROLL_START_DAY = 60
Mortality.DEFAULT_FEMALE_DEATH_DAY = 190
Mortality.DEFAULT_MALE_DEATH_DAY = 250
Mortality.NEVER = -1

local function integer(value, fallback)
    return math.floor(tonumber(value) or fallback)
end

function Mortality.configuration(source)
    source = source or (SandboxVars and SandboxVars.TGSRRRanchMortality)
    if type(source) ~= "table" then source = {} end

    local enabled = source.Enabled == true
    return {
        enabled = enabled,
        rollStartDay = enabled and math.max(0, integer(
            source.RollStartDay,
            Mortality.DEFAULT_ROLL_START_DAY))
            or Mortality.DEFAULT_ROLL_START_DAY,
        femaleDeathDay = enabled and integer(
            source.FemaleDeathDay,
            Mortality.DEFAULT_FEMALE_DEATH_DAY)
            or Mortality.DEFAULT_FEMALE_DEATH_DAY,
        maleDeathDay = enabled and integer(
            source.MaleDeathDay,
            Mortality.DEFAULT_MALE_DEATH_DAY)
            or Mortality.DEFAULT_MALE_DEATH_DAY,
    }
end

function Mortality.deathDayForSex(sex, config)
    config = config or Mortality.configuration()
    if sex == "female" then return config.femaleDeathDay end
    if sex == "male" then return config.maleDeathDay end
    return Mortality.NEVER
end

function Mortality.shouldSpawnDead(sex, worldAgeDays, source)
    local config = Mortality.configuration(source)
    local deathDay = Mortality.deathDayForSex(sex, config)
    if deathDay == Mortality.NEVER then return false end

    worldAgeDays = math.floor(tonumber(worldAgeDays) or 0)
    if worldAgeDays <= config.rollStartDay then return false end

    local oneIn = math.max(0, deathDay - worldAgeDays)
    if oneIn <= 1 then return true end
    return ZombRand(oneIn) == 0
end

return Mortality
