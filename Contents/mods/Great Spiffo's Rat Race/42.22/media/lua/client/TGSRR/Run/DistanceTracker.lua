local Recorder = require("TGSRR/Run/Recorder")
local DistanceTracker = {}
local activeRun, activePlayer
local previousX, previousY, previousTimestamp, previousVehicle, previousMode

local function finite(value)
    return type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function mode(player)
    local vehicle = player:getVehicle()
    if not vehicle then return "onFoot", nil end
    return vehicle:isDriver(player) and "driver" or nil, vehicle
end

function DistanceTracker.sample(player, now)
    if not activeRun or player ~= activePlayer then return end
    now = now or getTimestampMs()
    local x, y = player:getX(), player:getY()
    local currentMode, vehicle = mode(player)
    local elapsed = previousTimestamp and now - previousTimestamp or 0
    if activeRun.lifecycle == "active" and Recorder.isActive()
            and finite(x) and finite(y) and previousX and previousY
            and currentMode and currentMode == previousMode and vehicle == previousVehicle
            and elapsed >= 0 and elapsed <= 1000 then
        local dx, dy = x - previousX, y - previousY
        local squared = dx * dx + dy * dy
        if squared > 0 then
            -- Tick sampling preserves bends without allocations or a position trail.
            -- Scale the plausibility bound for accelerated simulation, not totals.
            local speed = math.max(1, getGameTime():getMultiplier())
            local limit = math.min(50, math.max(5, elapsed * 0.06 * speed))
            if squared <= limit * limit then
                local distance = math.sqrt(squared)
                activeRun.distanceTravelledMeters = activeRun.distanceTravelledMeters + distance
                local totals = activeRun.distanceByModeMeters
                totals[currentMode] = totals[currentMode] + distance
            else
                activeRun.distanceRejectedSamples = activeRun.distanceRejectedSamples + 1
            end
        end
    end
    previousX = finite(x) and x or nil
    previousY = finite(y) and y or nil
    previousTimestamp, previousMode, previousVehicle = now, currentMode, vehicle
end

function DistanceTracker.initialize(run, player, created)
    activeRun, activePlayer = run, player
    if not run.distanceByModeMeters then
        run.distanceByModeMeters = { onFoot = 0, driver = 0 }
        run.distanceModesPartial = created ~= true or run.bootstrapped == true
        if run.dailyState then run.dailyState.distanceModesPartial = true end
    end
    previousX, previousY, previousTimestamp, previousVehicle, previousMode = nil, nil, nil, nil, nil
    DistanceTracker.sample(player)
end

function DistanceTracker.reset()
    activeRun, activePlayer = nil, nil
    previousX, previousY, previousTimestamp, previousVehicle, previousMode = nil, nil, nil, nil, nil
end

function DistanceTracker.onTick()
    if activePlayer then DistanceTracker.sample(activePlayer) end
end

Events.OnTick.Add(DistanceTracker.onTick)
return DistanceTracker
