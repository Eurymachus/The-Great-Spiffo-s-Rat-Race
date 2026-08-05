local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"

local TerminalState = {}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

function TerminalState.markDeceased(player)
    local run = Identity.get()
    if type(run) ~= "table" or not nonEmpty(run.runId) then
        return false, "missing_run"
    end
    if run.lifecycle == "deceased" then return true, "already_deceased" end
    if run.lifecycle ~= "active" then
        return false, "run_already_ended:" .. tostring(run.lifecycle)
    end

    local recorded, result = Recorder.record("run.ended", {
        reason = "deceased",
        character = Identity.observeCharacter(player),
    })
    if not recorded then return false, result end

    run.lifecycle = "deceased"
    run.endedReason = "deceased"
    run.endedUtc = result.utc
    run.endedWorldAgeHours = result.worldAgeHours
    run.endedEventSequence = result.sequence
    run.endedEventHash = result.hash
    return true, result
end

return TerminalState
