local Locations = require "TGSRR/Locations/Definitions"
local Recorder = require "TGSRR/Run/Recorder"

local LocationTracker = {}

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
    local state = activeRun.locations
    local location, point =
        Locations.findAt(activePlayer:getX(), activePlayer:getY())
    if not location or state.visits[location.id] then return end

    local x = math.floor(tonumber(activePlayer:getX()) or point.x)
    local y = math.floor(tonumber(activePlayer:getY()) or point.y)
    local recorded, event = Recorder.record("location.visited", {
        locationId = location.id,
        pointId = point.id,
        x = x,
        y = y,
    })
    if not recorded then return end

    state.visits[location.id] = {
        utc = event.utc,
        worldAgeHours = event.worldAgeHours,
        pointId = point.id,
        x = x,
        y = y,
    }
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Locations] Visited " .. location.id .. " via "
            .. point.id .. " at " .. x .. "," .. y)
    end
end

local function onPlayerUpdate(player)
    if player ~= activePlayer or #Locations.getAll() == 0 then return end
    local now = milliseconds()
    if now - lastCheckMilliseconds < CHECK_INTERVAL_MILLISECONDS then return end
    lastCheckMilliseconds = now
    observe()
end

function LocationTracker.initialize(run, player, created)
    activeRun = run
    activePlayer = player
    lastCheckMilliseconds = 0

    local registryVersion = Locations.getVersion()
    if type(run.locations) ~= "table" then
        run.locations = {
            schema = 1,
            registryVersion = registryVersion,
            partial = registryVersion > 0
                and (not created or run.bootstrapped == true) or false,
            visits = {},
        }
    else
        run.locations.visits = type(run.locations.visits) == "table"
            and run.locations.visits or {}
        local previousVersion =
            math.max(0, math.floor(tonumber(run.locations.registryVersion) or 0))
        if previousVersion ~= registryVersion then
            run.locations.partial = true
            run.locations.registryVersion = registryVersion
        end
    end
    if #Locations.getAll() > 0 then observe() end
end

Events.OnPlayerUpdate.Add(onPlayerUpdate)

return LocationTracker
