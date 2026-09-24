local DistanceTracker = {}

local MAX_SPEED_TILES_PER_SECOND = 60
local MIN_ALLOWED_STEP_TILES = 5
local MAX_ALLOWED_STEP_TILES = 50

local activeRun = nil
local activePlayer = nil
local previousX = nil
local previousY = nil
local previousTimestamp = nil

local function timestampMilliseconds()
    if getTimestampMs then return tonumber(getTimestampMs()) end
    return nil
end

local function resetSample(player)
    previousX = tonumber(player and player:getX()) or nil
    previousY = tonumber(player and player:getY()) or nil
    previousTimestamp = timestampMilliseconds()
end

local function allowedStep(now)
    if not now or not previousTimestamp or now <= previousTimestamp then
        return MIN_ALLOWED_STEP_TILES
    end
    local elapsedSeconds = (now - previousTimestamp) / 1000
    return math.min(MAX_ALLOWED_STEP_TILES,
        math.max(MIN_ALLOWED_STEP_TILES,
            elapsedSeconds * MAX_SPEED_TILES_PER_SECOND))
end

function DistanceTracker.sample(player, now)
    if not activeRun or player ~= activePlayer then return end
    local x = tonumber(player:getX())
    local y = tonumber(player:getY())
    now = tonumber(now) or timestampMilliseconds()
    if not x or not y or not previousX or not previousY then
        resetSample(player)
        return
    end

    local dx = x - previousX
    local dy = y - previousY
    local distance = math.sqrt(dx * dx + dy * dy)
    if distance > 0 and distance <= allowedStep(now) then
        activeRun.distanceTravelledMeters =
            math.max(0, tonumber(activeRun.distanceTravelledMeters) or 0)
                + distance
    elseif distance > 0 then
        activeRun.distanceRejectedSamples =
            math.max(0, math.floor(
                tonumber(activeRun.distanceRejectedSamples) or 0)) + 1
    end

    previousX, previousY, previousTimestamp = x, y, now
end

function DistanceTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    resetSample(player)
end

function DistanceTracker.reset()
    activeRun = nil
    activePlayer = nil
    previousX, previousY, previousTimestamp = nil, nil, nil
end

Events.OnPlayerMove.Add(DistanceTracker.sample)

return DistanceTracker
