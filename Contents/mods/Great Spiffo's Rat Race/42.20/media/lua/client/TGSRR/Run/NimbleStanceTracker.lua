local Recorder = require "TGSRR/Run/Recorder"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"
local Clock = require "TGSRR/Run/ActiveGameplayClock"

local NimbleStanceTracker = {}

local MAX_SAMPLE_INTERVAL_MILLISECONDS = 1000

local activeRun = nil
local activePlayer = nil
local previousX = nil
local previousY = nil
local previousTimestamp = nil
local previousEligible = false

local function milliseconds()
    return Clock.milliseconds()
end

local function isFishing(player)
    if not player or not player.isCurrentState then return false end
    if not FishingState or not FishingState.instance then return false end
    return player:isCurrentState(FishingState.instance())
end

local function eligible(player)
    if not player or player:isDead() then return false end
    if Clock.isPaused(player) then return false end
    if player:getVehicle() then return false end
    if not player:isAiming() then return false end
    if isFishing(player) then return false end
    return true
end

local function resetSample(player, now)
    previousX = tonumber(player and player:getX()) or nil
    previousY = tonumber(player and player:getY()) or nil
    previousTimestamp = tonumber(now) or milliseconds()
    previousEligible = eligible(player)
end

function NimbleStanceTracker.sample(now)
    if not activeRun or not activePlayer or not Recorder.isActive() then
        return
    end
    now = tonumber(now) or milliseconds()
    local x = tonumber(activePlayer:getX())
    local y = tonumber(activePlayer:getY())
    if not now or not x or not y or not previousTimestamp
            or not previousX or not previousY then
        resetSample(activePlayer, now)
        return
    end

    local elapsed = now - previousTimestamp
    local currentEligible = eligible(activePlayer)
    local moved = x ~= previousX or y ~= previousY
    if elapsed > 0 and elapsed <= MAX_SAMPLE_INTERVAL_MILLISECONDS
            and moved and previousEligible and currentEligible then
        activeRun.nimbleStanceMovementMilliseconds =
            math.max(0, tonumber(
                activeRun.nimbleStanceMovementMilliseconds) or 0)
                + elapsed
    end

    previousX = x
    previousY = y
    previousTimestamp = now
    previousEligible = currentEligible
end

function NimbleStanceTracker.onTick()
    local ok, reason = pcall(NimbleStanceTracker.sample)
    if ok then return end
    local failure = "nimble_stance_collector_failed:"
        .. tostring(reason or "unknown_error")
    if activeRun then activeRun.integrityStatus = failure end
    Recorder.deactivate()
    activeRun = nil
    activePlayer = nil
    previousX = nil
    previousY = nil
    previousTimestamp = nil
    previousEligible = false
    TrackingHealth.stop(
        failure,
        "Nimble-stance movement time could not be recorded."
    )
end

function NimbleStanceTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    resetSample(player)
    return true
end

function NimbleStanceTracker.reset()
    activeRun = nil
    activePlayer = nil
    previousX = nil
    previousY = nil
    previousTimestamp = nil
    previousEligible = false
end

Events.OnTick.Add(NimbleStanceTracker.onTick)

return NimbleStanceTracker
