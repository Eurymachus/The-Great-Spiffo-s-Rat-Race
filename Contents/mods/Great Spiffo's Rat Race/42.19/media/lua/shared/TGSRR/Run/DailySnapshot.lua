local Identity = require "TGSRR/Run/Identity"
local SkillSnapshot = require "TGSRR/Run/SkillSnapshot"
local WeaponKillSnapshot = require "TGSRR/Run/WeaponKillSnapshot"

local DailySnapshot = {}

function DailySnapshot.current(player, run)
    return {
        kills = math.max(0, tonumber(player and player:getZombieKills()) or 0),
        skills = SkillSnapshot.totals(player),
        weaponKills = WeaponKillSnapshot.copy(run and run.weaponKills),
        fireDeaths = math.max(0, tonumber(run and run.fireDeaths) or 0),
    }
end

function DailySnapshot.deltas(current, baseline)
    local result = {}
    local keys = {}
    for id in pairs(current or {}) do keys[id] = true end
    for id in pairs(baseline or {}) do keys[id] = true end
    for id in pairs(keys) do
        local delta = (tonumber(current[id]) or 0) - (tonumber(baseline[id]) or 0)
        if delta ~= 0 then result[id] = delta end
    end
    return result
end

function DailySnapshot.active(run, player)
    local baseline = run and run.dailyState or nil
    if type(baseline) ~= "table" then return nil end
    local current = DailySnapshot.current(player, run)
    local gameTime = getGameTime and getGameTime() or nil
    local currentWorldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
    local startedWorldAgeHours = tonumber(baseline.startedWorldAgeHours) or 0
    return {
        dayIndex = math.max(1, math.floor(tonumber(baseline.dayIndex) or 1)),
        baselinePartial = baseline.partial == true,
        startedUtc = math.max(0, math.floor(tonumber(baseline.startedUtc) or 0)),
        startedWorldAgeHours = startedWorldAgeHours,
        observedUtc = Identity.utcSeconds(),
        observedWorldAgeHours = currentWorldAgeHours,
        elapsedWorldHours = math.max(0, currentWorldAgeHours - startedWorldAgeHours),
        killDelta = current.kills - (tonumber(baseline.kills) or 0),
        xpDeltas = DailySnapshot.deltas(current.skills, baseline.skills),
        weaponKillDeltas =
            DailySnapshot.deltas(current.weaponKills, baseline.weaponKills),
        weaponKillsPartial = baseline.weaponKillsPartial == true,
        fireDeathDelta =
            current.fireDeaths - (tonumber(baseline.fireDeaths) or 0),
        fireDeathsPartial = baseline.fireDeathsPartial == true,
    }
end

return DailySnapshot
