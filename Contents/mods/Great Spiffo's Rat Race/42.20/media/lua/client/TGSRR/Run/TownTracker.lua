local Towns = require "TGSRR/Towns/Definitions"
local Recorder = require "TGSRR/Run/Recorder"

local TownTracker = {}

local activeRun = nil
local activePlayer = nil
local lastCheckMilliseconds = 0

local CHECK_INTERVAL_MILLISECONDS = 1000

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function observe()
    if not activeRun or not activePlayer then return end
    activeRun.townVisits = type(activeRun.townVisits) == "table"
        and activeRun.townVisits or {}

    local town, point = Towns.findAt(activePlayer:getX(), activePlayer:getY())
    if not town or activeRun.townVisits[town.id] then return end

    local x = math.floor(tonumber(activePlayer:getX()) or point.x)
    local y = math.floor(tonumber(activePlayer:getY()) or point.y)
    local recorded, event = Recorder.record("town.visited", {
        townId = town.id,
        pointId = point.id,
        x = x,
        y = y,
    })
    if not recorded then return end

    activeRun.townVisits[town.id] = {
        utc = event.utc,
        worldAgeHours = event.worldAgeHours,
        pointId = point.id,
        x = x,
        y = y,
    }
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Towns] Visited " .. town.id .. " via " .. point.id
            .. " at " .. x .. "," .. y)
    end
end

local function onPlayerUpdate(player)
    if player ~= activePlayer then return end
    local now = milliseconds()
    if now - lastCheckMilliseconds < CHECK_INTERVAL_MILLISECONDS then return end
    lastCheckMilliseconds = now
    observe()
end

function TownTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    lastCheckMilliseconds = 0
    run.townVisits = type(run.townVisits) == "table" and run.townVisits or {}
    observe()
end

Events.OnPlayerUpdate.Add(onPlayerUpdate)

return TownTracker
