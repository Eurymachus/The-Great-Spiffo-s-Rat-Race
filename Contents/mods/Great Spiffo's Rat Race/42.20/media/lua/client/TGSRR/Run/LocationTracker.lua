local Locations = require "TGSRR/Locations/Definitions"
local Recorder = require "TGSRR/Run/Recorder"
local Identity = require "TGSRR/Run/Identity"

local LocationTracker = {}

local activeRun = nil
local activePlayer = nil
local lastCheckMilliseconds = 0
local lastBuildingId = nil

local CHECK_INTERVAL_MILLISECONDS = 1000

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function recordBuildingVisit(buildingDef)
    if not activeRun or not activePlayer or not buildingDef then
        lastBuildingId = nil
        return nil
    end

    local buildingId = tostring(buildingDef:getIDString() or "")
    if buildingId == "" then
        lastBuildingId = nil
        return nil
    end
    if buildingId == lastBuildingId then return buildingId end
    lastBuildingId = buildingId

    local visits = activeRun.buildingVisits
    if visits[buildingId] then return buildingId end

    local gameTime = getGameTime and getGameTime() or nil
    visits[buildingId] = {
        utc = Identity.utcSeconds(),
        worldAgeHours = gameTime
            and tonumber(gameTime:getWorldAgeHours()) or 0,
        year = gameTime and tonumber(gameTime:getYear()) or 0,
        month = gameTime and (tonumber(gameTime:getMonth()) or 0) + 1 or 0,
        day = gameTime and (tonumber(gameTime:getDay()) or 0) + 1 or 0,
        timeOfDay = gameTime and tonumber(gameTime:getTimeOfDay()) or 0,
        x = math.floor(tonumber(activePlayer:getX()) or 0),
        y = math.floor(tonumber(activePlayer:getY()) or 0),
        z = math.floor(tonumber(activePlayer:getZ()) or 0),
    }

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Buildings] First visit " .. buildingId
            .. " at " .. visits[buildingId].x
            .. "," .. visits[buildingId].y
            .. "," .. visits[buildingId].z)
    end
    return buildingId
end

local function observe()
    if not activeRun or not activePlayer then return end
    local state = activeRun.locations
    local location, point, buildingId, discoveryMethod
    local square = activePlayer:getCurrentSquare()
    local building = square and square:getBuilding()
    local buildingDef = building and building:getDef()
    if buildingDef then
        buildingId = recordBuildingVisit(buildingDef)
        location = Locations.findByBuildingId(buildingId)
        if location then discoveryMethod = "building" end
    else
        lastBuildingId = nil
    end
    if not location then
        location, point = Locations.findAt(
            activePlayer:getX(), activePlayer:getY())
        if location then discoveryMethod = "point" end
    end
    if not location or state.visits[location.id] then return end

    local x = math.floor(tonumber(activePlayer:getX()) or point.x)
    local y = math.floor(tonumber(activePlayer:getY()) or point.y)
    local recorded, event = Recorder.record("location.visited", {
        locationId = location.id,
        buildingId = buildingId or "",
        pointId = point and point.id or "",
        discoveryMethod = discoveryMethod,
        x = x,
        y = y,
    })
    if not recorded then return end

    state.visits[location.id] = {
        utc = event.utc,
        worldAgeHours = event.worldAgeHours,
        buildingId = buildingId or "",
        pointId = point and point.id or "",
        discoveryMethod = discoveryMethod,
        x = x,
        y = y,
    }
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Landmarks] Discovered " .. location.id .. " via "
            .. tostring(discoveryMethod) .. " at " .. x .. "," .. y)
    end
end

function LocationTracker.getSnapshot()
    local Snapshot = require "TGSRR/Run/LocationSnapshot"
    return Snapshot.observeForTracker(activeRun)
end

function LocationTracker.getBuildingVisit(buildingId)
    if not activeRun or type(activeRun.buildingVisits) ~= "table"
            or buildingId == nil then
        return nil
    end
    return activeRun.buildingVisits[tostring(buildingId)]
end

function LocationTracker.hasVisitedBuilding(buildingId)
    return LocationTracker.getBuildingVisit(buildingId) ~= nil
end

local function onPlayerUpdate(player)
    if player ~= activePlayer then return end
    local now = milliseconds()
    if now - lastCheckMilliseconds < CHECK_INTERVAL_MILLISECONDS then return end
    lastCheckMilliseconds = now
    observe()
end

function LocationTracker.initialize(run, player, created)
    activeRun = run
    activePlayer = player
    lastCheckMilliseconds = 0
    lastBuildingId = nil

    if type(run.buildingVisits) ~= "table" then
        run.buildingVisits = {}
        run.buildingVisitsPartial = not created or run.bootstrapped == true
    end
    run.buildingVisitsPartial = run.buildingVisitsPartial == true

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
    observe()
end

Events.OnPlayerUpdate.Add(onPlayerUpdate)

return LocationTracker
