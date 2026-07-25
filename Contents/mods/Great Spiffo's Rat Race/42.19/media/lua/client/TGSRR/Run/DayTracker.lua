local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"
local DailySnapshot = require "TGSRR/Run/DailySnapshot"

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
            weaponKillDeltas =
                deltas(current.weaponKills, previousState.weaponKills),
            weaponKillsPartial = previousState.weaponKillsPartial == true,
            fireDeathDelta =
                current.fireDeaths - (tonumber(previousState.fireDeaths) or 0),
            fireDeathsPartial = previousState.fireDeathsPartial == true,
            distanceDeltaMeters = math.max(0,
                current.distanceTravelledMeters
                    - (tonumber(previousState.distanceTravelledMeters) or 0)),
            distancePartial = previousState.distancePartial == true,
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
            weaponKills = current.weaponKills,
            weaponKillsPartial =
                initial == true and activeRun.weaponKillsPartial == true,
            fireDeaths = current.fireDeaths,
            fireDeathsPartial =
                initial == true and activeRun.fireDeathsPartial == true,
            distanceTravelledMeters = current.distanceTravelledMeters,
            distancePartial =
                initial == true and activeRun.distanceTravelledPartial == true,
        },
        previousDay = previousDay,
    }, {
        utc = utc,
        worldAgeHours = worldAgeHours,
    })
    if not ok then return false, record end

    activeRun.dailyState = {
        dayIndex = dayIndex,
        partial = initial == true and activeRun.bootstrapped == true,
        startedUtc = record.utc,
        startedWorldAgeHours = record.worldAgeHours,
        kills = current.kills,
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
