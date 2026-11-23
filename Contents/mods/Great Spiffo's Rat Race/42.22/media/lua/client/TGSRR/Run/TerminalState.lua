local Identity = require("TGSRR/Run/Identity")
local Recorder = require("TGSRR/Run/Recorder")
local DeathEvidence = require("TGSRR/Run/DeathEvidence")

local TerminalState = {}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

function TerminalState.markDeceased(player, context)
    local run = Identity.get()
    if type(run) ~= "table" or not nonEmpty(run.runId) then
        return false, "missing_run"
    end
    if run.lifecycle == "deceased" then return true, "already_deceased" end
    if run.lifecycle ~= "active" then
        return false, "run_already_ended:" .. tostring(run.lifecycle)
    end

    local evidence = DeathEvidence.capture(player, context)
    local recorded, result = Recorder.record("run.ended", {
        reason = "deceased",
        character = Identity.observeCharacter(player),
        deathEvidence = evidence,
    })
    if not recorded then return false, result end

    run.lifecycle = "deceased"
    run.endedReason = "deceased"
    run.endedUtc = result.utc
    run.endedWorldAgeHours = result.worldAgeHours
    run.endedEventSequence = result.sequence
    run.endedEventHash = result.hash
    run.deathEvidence = evidence
    local location = evidence.location
    local recentSources = {}
    for _, observation in ipairs(evidence.recentDamage) do
        recentSources[#recentSources + 1] = observation.source .. "@"
            .. tostring(observation.ageMilliseconds) .. "ms"
    end
    print("[TGSRR Run] Death evidence: cause=" .. evidence.cause
        .. " certainty=" .. evidence.certainty
        .. " infectedAtDeath=" .. tostring(evidence.infectedAtDeath)
        .. " sleepingPillsTaken=" .. tostring(evidence.medication and evidence.medication.sleepingPillsTaken)
        .. " intoxication=" .. tostring(evidence.medication and evidence.medication.intoxication)
        .. " lastDamageSource=" .. evidence.lastDamageSource
        .. " context=" .. evidence.captureContext
        .. " location=" .. (location and (tostring(location.x) .. ","
            .. tostring(location.y) .. "," .. tostring(location.z)) or "unknown")
        .. " recent=" .. table.concat(recentSources, ","))
    return true, result
end

return TerminalState
