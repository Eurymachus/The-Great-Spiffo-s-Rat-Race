local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"

local DayTracker = {}

local activeRun = nil
local activePlayer = nil

local function skillTotals(player)
    local result = {}
    local xp = player and player.getXp and player:getXp() or nil
    local perks = PerkFactory and PerkFactory.PerkList or nil
    if not xp or not perks then return result end

    for index = 0, perks:size() - 1 do
        local perk = perks:get(index)
        if perk and perk:getParent() ~= Perks.None then
            local perkType = perk:getType()
            result[tostring(perkType)] = tonumber(xp:getXP(perkType)) or 0
        end
    end
    return result
end

local function snapshot(player)
    return {
        kills = math.max(0, tonumber(player and player:getZombieKills()) or 0),
        skills = skillTotals(player),
    }
end

local function deltas(current, baseline)
    local result = {}
    local keys = {}
    for id, _ in pairs(current or {}) do keys[id] = true end
    for id, _ in pairs(baseline or {}) do keys[id] = true end
    for id, _ in pairs(keys) do
        local delta = (tonumber(current[id]) or 0) - (tonumber(baseline[id]) or 0)
        if delta ~= 0 then result[id] = delta end
    end
    return result
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

local function beginDay(initial)
    if not activeRun or not activePlayer or not Recorder.isActive() then return false end
    local current = snapshot(activePlayer)
    local previousState = activeRun.dailyState
    local dayIndex = previousState and (tonumber(previousState.dayIndex) or 0) + 1
        or math.floor(math.max(0, tonumber(activePlayer:getHoursSurvived()) or 0) / 24) + 1
    local previousDay = nil
    if previousState then
        previousDay = {
            dayIndex = tonumber(previousState.dayIndex) or math.max(1, dayIndex - 1),
            startedUtc = tonumber(previousState.startedUtc) or 0,
            startedWorldAgeHours = tonumber(previousState.startedWorldAgeHours) or 0,
            killDelta = current.kills - (tonumber(previousState.kills) or 0),
            xpDeltas = deltas(current.skills, previousState.skills),
        }
    end

    local gameTime = getGameTime and getGameTime() or nil
    local utc = Identity.utcSeconds()
    local worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
    local ok, record = Recorder.record("day.started", {
        dayIndex = dayIndex,
        calendar = calendar(),
        partial = initial == true and activeRun.bootstrapped == true,
        baseline = {
            kills = current.kills,
            skills = current.skills,
        },
        previousDay = previousDay,
    }, {
        utc = utc,
        worldAgeHours = worldAgeHours,
    })
    if not ok then return false, record end

    activeRun.dailyState = {
        dayIndex = dayIndex,
        startedUtc = record.utc,
        startedWorldAgeHours = record.worldAgeHours,
        kills = current.kills,
        skills = current.skills,
    }
    return true
end

function DayTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    if type(run.dailyState) ~= "table" then return beginDay(true) end
    return true
end

function DayTracker.onNewDay()
    return beginDay(false)
end

Events.EveryDays.Add(DayTracker.onNewDay)

return DayTracker
