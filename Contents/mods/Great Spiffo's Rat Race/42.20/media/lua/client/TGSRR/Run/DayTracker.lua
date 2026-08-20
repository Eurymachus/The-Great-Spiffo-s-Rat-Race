local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"
local DailySnapshot = require "TGSRR/Run/DailySnapshot"
local AnimalTrapSnapshot = require "TGSRR/Run/AnimalTrapSnapshot"
local InjurySnapshot = require "TGSRR/Run/InjurySnapshot"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"

local DayTracker = {}

local activeRun = nil
local activePlayer = nil

local function snapshot(player)
    return DailySnapshot.current(player, activeRun)
end

local function deltas(current, baseline)
    return DailySnapshot.deltas(current, baseline)
end

local function calendar()
    local gameTime = getGameTime and getGameTime() or nil
    if not gameTime then return nil end
    return {
        year = tonumber(gameTime:getYear()) or 0,
        month = (tonumber(gameTime:getMonth()) or 0) + 1,
        day = tonumber(gameTime:getDay()) or 0,
    }
end

local function nonEmpty(values)
    if type(values) ~= "table" then return false end
    for _ in pairs(values) do return true end
    return false
end

local function addDelta(target, key, value)
    value = tonumber(value) or 0
    if value ~= 0 then target[key] = value end
end

local function addDeltas(target, key, values)
    if nonEmpty(values) then target[key] = values end
end

local function completedDay(current, previousState, dayIndex)
    if not previousState then return nil end
    local result = {
        dayIndex = tonumber(previousState.dayIndex)
            or math.max(1, dayIndex - 1),
        startedUtc = tonumber(previousState.startedUtc) or 0,
        startedWorldAgeHours =
            tonumber(previousState.startedWorldAgeHours) or 0,
    }
    addDelta(result, "killDelta",
        current.kills - (tonumber(previousState.kills) or 0))
    addDelta(result, "weightDeltaKilograms",
        current.weightKilograms
            - (tonumber(previousState.weightKilograms) or 0))
    addDeltas(result, "xpDeltas",
        deltas(current.skills, previousState.skills))
    addDeltas(result, "weaponKillDeltas",
        deltas(current.weaponKills, previousState.weaponKills))
    addDelta(result, "fireDeathDelta",
        current.fireDeaths - (tonumber(previousState.fireDeaths) or 0))
    addDelta(result, "distanceDeltaMeters", math.max(0,
        current.distanceTravelledMeters
            - (tonumber(previousState.distanceTravelledMeters) or 0)))
    addDeltas(result, "brokenWeaponDeltas",
        deltas(current.brokenWeapons, previousState.brokenWeapons))
    addDeltas(result, "animalSlaughterDeltas",
        deltas(current.animalsSlaughtered,
            previousState.animalsSlaughtered))
    addDeltas(result, "animalTrapDeltas",
        AnimalTrapSnapshot.deltaPairs(
            current.animalsTrapped, previousState.animalsTrapped))
    addDeltas(result, "animalBirthDeltas",
        deltas(current.animalBirths, previousState.animalBirths))
    addDeltas(result, "animalPetDeltas",
        deltas(current.animalsPetted, previousState.animalsPetted))
    addDeltas(result, "milkCollectedDeltas",
        deltas(current.milkCollected, previousState.milkCollected))
    addDelta(result, "butterProducedDelta",
        current.butterProduced - math.max(0,
            math.floor(tonumber(previousState.butterProduced) or 0)))
    addDeltas(result, "fishCaughtDeltas",
        deltas(current.fishCaught, previousState.fishCaught))
    addDeltas(result, "injuryDeltas",
        InjurySnapshot.deltaPairs(
            current.injuries, previousState.injuries))
    addDeltas(result, "zombieAssociatedInjuryDeltas",
        InjurySnapshot.deltaPairs(
            current.zombieAssociatedInjuries,
            previousState.zombieAssociatedInjuries))
    addDeltas(result, "fluidConsumedDeltas",
        deltas(current.fluidConsumed, previousState.fluidConsumed))
    addDelta(result, "caloriesConsumedDelta",
        current.caloriesConsumed
            - (tonumber(previousState.caloriesConsumed) or 0))
    addDelta(result, "generatorRepairDelta",
        current.generatorRepairs - math.max(0,
            math.floor(tonumber(previousState.generatorRepairs) or 0)))
    addDelta(result, "generatorConditionRestoredDelta",
        current.generatorConditionRestored
            - (tonumber(previousState.generatorConditionRestored) or 0))
    addDelta(result, "nimbleMovementMillisecondsDelta",
        current.nimbleMovementMilliseconds
            - (tonumber(previousState.nimbleMovementMilliseconds) or 0))
    addDelta(result, "activeGameplayMillisecondsDelta",
        current.activeGameplayMilliseconds
            - (tonumber(previousState.activeGameplayMilliseconds) or 0))

    local partialMetrics = {}
    local partialFields = {
        { "weaponKills", "weaponKillsPartial" },
        { "fireDeaths", "fireDeathsPartial" },
        { "distance", "distancePartial" },
        { "brokenWeapons", "brokenWeaponsPartial" },
        { "animalsSlaughtered", "animalsSlaughteredPartial" },
        { "animalsTrapped", "animalsTrappedPartial" },
        { "animalBirths", "animalBirthsPartial" },
        { "animalsPetted", "animalsPettedPartial" },
        { "milkCollected", "milkCollectedPartial" },
        { "butterProduced", "butterProducedPartial" },
        { "fishCaught", "fishCaughtPartial" },
        { "injuries", "injuriesPartial" },
        { "fluidConsumed", "fluidConsumedPartial" },
        { "caloriesConsumed", "caloriesConsumedPartial" },
        { "generatorRepairs", "generatorRepairsPartial" },
        { "nimbleStance", "nimbleStancePartial" },
        { "activeGameplay", "activeGameplayPartial" },
    }
    for _, entry in ipairs(partialFields) do
        if previousState[entry[2]] == true then
            partialMetrics[#partialMetrics + 1] = entry[1]
        end
    end
    if previousState.partial == true then result.partial = true end
    if #partialMetrics > 0 then
        result.partialMetrics = partialMetrics
    end
    return result
end

local function beginDay(initial)
    if not activeRun or not activePlayer or not Recorder.isActive() then return false end
    local current = snapshot(activePlayer)
    local previousState = activeRun.dailyState
    local dayIndex = previousState and (tonumber(previousState.dayIndex) or 0) + 1
        or math.floor(math.max(0, tonumber(activePlayer:getHoursSurvived()) or 0) / 24) + 1
    local gameTime = getGameTime and getGameTime() or nil
    local utc = Identity.utcSeconds()
    local worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
    local currentCalendar = calendar()
    local ok, record = Recorder.record("day.started", {
        dayIndex = dayIndex,
        calendar = currentCalendar,
        partial = initial == true
            and activeRun.bootstrapped == true or nil,
        completedDay = completedDay(
            current, previousState, dayIndex),
    }, {
        utc = utc,
        worldAgeHours = worldAgeHours,
    })
    if not ok then return false, record end

    activeRun.dailyState = {
        dayIndex = dayIndex,
        partial = initial == true and activeRun.bootstrapped == true,
        calendar = currentCalendar,
        startedUtc = record.utc,
        startedWorldAgeHours = record.worldAgeHours,
        kills = current.kills,
        weightKilograms = current.weightKilograms,
        skills = current.skills,
        weaponKills = current.weaponKills,
        weaponKillsPartial =
            initial == true and activeRun.weaponKillsPartial == true,
        fireDeaths = current.fireDeaths,
        fireDeathsPartial =
            initial == true and activeRun.fireDeathsPartial == true,
        distanceTravelledMeters = current.distanceTravelledMeters,
        distancePartial =
            initial == true and activeRun.distanceTravelledPartial == true,
        brokenWeapons = current.brokenWeapons,
        brokenWeaponsPartial =
            initial == true and activeRun.brokenWeaponsPartial == true,
        animalsSlaughtered = current.animalsSlaughtered,
        animalsSlaughteredPartial =
            initial == true and activeRun.animalsSlaughteredPartial == true,
        animalsTrapped = current.animalsTrapped,
        animalsTrappedPartial =
            initial == true and activeRun.animalsTrappedPartial == true,
        animalBirths = current.animalBirths,
        animalBirthsPartial =
            initial == true and activeRun.animalBirthsPartial == true,
        animalsPetted = current.animalsPetted,
        animalsPettedPartial =
            initial == true and activeRun.animalsPettedPartial == true,
        milkCollected = current.milkCollected,
        milkCollectedPartial =
            initial == true and activeRun.milkCollectedPartial == true,
        butterProduced = current.butterProduced,
        butterProducedPartial =
            initial == true and activeRun.butterProducedPartial == true,
        fishCaught = current.fishCaught,
        fishCaughtPartial =
            initial == true and activeRun.fishCaughtPartial == true,
        injuries = current.injuries,
        zombieAssociatedInjuries =
            current.zombieAssociatedInjuries,
        injuriesPartial =
            initial == true and activeRun.injuriesPartial == true,
        fluidConsumed = current.fluidConsumed,
        fluidConsumedPartial =
            initial == true and activeRun.fluidConsumedPartial == true,
        caloriesConsumed = current.caloriesConsumed,
        caloriesConsumedPartial =
            initial == true and activeRun.caloriesConsumedPartial == true,
        generatorRepairs = current.generatorRepairs,
        generatorConditionRestored = current.generatorConditionRestored,
        generatorRepairsPartial =
            initial == true and activeRun.generatorRepairsPartial == true,
        nimbleMovementMilliseconds = current.nimbleMovementMilliseconds,
        nimbleStancePartial =
            initial == true and activeRun.nimbleStanceMovementPartial == true,
        activeGameplayMilliseconds = current.activeGameplayMilliseconds,
        activeGameplayPartial =
            initial == true and activeRun.activeGameplayPartial == true,
    }
    return true
end

function DayTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    if type(run.dailyState) ~= "table" then return beginDay(true) end
    local requiredMaps = {
        "skills", "weaponKills", "brokenWeapons",
        "animalsSlaughtered", "animalsTrapped", "animalBirths",
        "animalsPetted", "milkCollected", "fishCaught", "injuries",
        "fluidConsumed",
        "zombieAssociatedInjuries",
    }
    for _, field in ipairs(requiredMaps) do
        if type(run.dailyState[field]) ~= "table" then
            return false, "invalid_daily_state:" .. field
        end
    end
    for _, field in ipairs({
        "dayIndex", "startedUtc", "startedWorldAgeHours", "kills",
        "weightKilograms", "fireDeaths", "distanceTravelledMeters",
        "butterProduced",
        "caloriesConsumed", "generatorRepairs",
        "generatorConditionRestored", "nimbleMovementMilliseconds",
        "activeGameplayMilliseconds",
    }) do
        if tonumber(run.dailyState[field]) == nil then
            return false, "invalid_daily_state:" .. field
        end
    end
    if type(run.dailyState.calendar) ~= "table"
            or tonumber(run.dailyState.calendar.year) == nil
            or tonumber(run.dailyState.calendar.month) == nil
            or tonumber(run.dailyState.calendar.day) == nil then
        return false, "invalid_daily_state:calendar"
    end
    return true
end

function DayTracker.onNewDay()
    local ok, result, reason = pcall(beginDay, false)
    if ok then return result, reason end
    local failure = "day_tracker_failed:"
        .. tostring(result or "unknown_error")
    if activeRun then activeRun.integrityStatus = failure end
    Recorder.deactivate()
    activeRun = nil
    activePlayer = nil
    TrackingHealth.stop(
        failure,
        "The survived-day boundary could not be recorded."
    )
    return false, failure
end

Events.EveryDays.Add(DayTracker.onNewDay)

return DayTracker
