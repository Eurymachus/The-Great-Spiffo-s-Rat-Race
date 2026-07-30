local Recorder = require "TGSRR/Run/Recorder"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"
local Clock = require "TGSRR/Run/ActiveGameplayClock"

local ActiveGameplayTracker = {}

local MAX_INTERVAL_MILLISECONDS = 5000

local activeRun = nil
local activePlayer = nil
local previousTimestamp = nil

local function resetTimestamp(now)
    previousTimestamp = tonumber(now) or Clock.milliseconds()
end

function ActiveGameplayTracker.sample(now)
    if not activeRun or not activePlayer or not Recorder.isActive() then
        return
    end
    now = tonumber(now) or Clock.milliseconds()
    if not now or not previousTimestamp then
        resetTimestamp(now)
        return
    end
    local elapsed = now - previousTimestamp
    previousTimestamp = now
    if Clock.isPaused(activePlayer) then return end
    if elapsed <= 0 or elapsed > MAX_INTERVAL_MILLISECONDS then return end
    activeRun.activeGameplayMilliseconds =
        math.max(0, tonumber(activeRun.activeGameplayMilliseconds) or 0)
            + elapsed
end

function ActiveGameplayTracker.onTick()
    local ok, reason = pcall(ActiveGameplayTracker.sample)
    if ok then return end
    local failure = "active_gameplay_collector_failed:"
        .. tostring(reason or "unknown_error")
    if activeRun then activeRun.integrityStatus = failure end
    Recorder.deactivate()
    activeRun = nil
    activePlayer = nil
    previousTimestamp = nil
    TrackingHealth.stop(
        failure,
        "Active gameplay time could not be recorded."
    )
end

function ActiveGameplayTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    resetTimestamp()
    return true
end

function ActiveGameplayTracker.reset()
    activeRun = nil
    activePlayer = nil
    previousTimestamp = nil
end

Events.OnTick.Add(ActiveGameplayTracker.onTick)

return ActiveGameplayTracker
