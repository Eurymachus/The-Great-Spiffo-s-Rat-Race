local Identity = require "TGSRR/Run/Identity"
local EventTypes = require "TGSRR/Run/EventTypes"
local Ledger = require "TGSRR/Run/Ledger"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"

local Recorder = {}

local activeRun = nil
local recording = false
local haltedReason = nil

local function halt(reason)
    reason = tostring(reason or "event_recording_failed")
    haltedReason = reason
    if activeRun then activeRun.integrityStatus = reason end
    print("[TGSRR Run] Event recording halted: " .. reason)
    TrackingHealth.stop(reason, "Event recording halted.")
    return false, reason
end

function Recorder.activate(run)
    if type(run) ~= "table" or not run.runId then return false, "invalid_run" end
    activeRun = run
    recording = false
    haltedReason = nil
    return true
end

function Recorder.deactivate()
    activeRun = nil
    recording = false
    haltedReason = nil
end

function Recorder.isActive()
    return activeRun ~= nil and haltedReason == nil
end

function Recorder.getActiveRun()
    return activeRun
end

function Recorder.record(eventType, payload, context)
    if not activeRun then return false, "recorder_inactive" end
    if haltedReason then return false, haltedReason end
    if recording then return halt("reentrant_event_recording") end
    if not EventTypes.isRegistered(eventType) then return false, "unregistered_event_type:" .. tostring(eventType) end

    context = context or {}
    local gameTime = getGameTime and getGameTime() or nil
    local event = {
        utc = tonumber(context.utc) or Identity.utcSeconds(),
        worldAgeHours = tonumber(context.worldAgeHours)
            or (gameTime and gameTime:getWorldAgeHours()) or 0,
        eventType = eventType,
        payload = payload or {},
    }

    recording = true
    local ok, result = Ledger.append(activeRun, event)
    recording = false
    if not ok then return halt(result) end

    activeRun.eventSequence = result.sequence
    activeRun.eventHash = result.hash
    activeRun.integrityStatus = "ok"
    return true, {
        sequence = result.sequence,
        hash = result.hash,
        eventType = eventType,
        utc = event.utc,
        worldAgeHours = event.worldAgeHours,
    }
end

function Recorder.registerType(name)
    return EventTypes.register(name)
end

return Recorder
