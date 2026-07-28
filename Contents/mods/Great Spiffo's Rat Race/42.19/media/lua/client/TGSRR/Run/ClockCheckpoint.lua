local EventCodec = require "TGSRR/Run/EventCodec"
local Hash = require "TGSRR/Run/Hash"
local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"

local ClockCheckpoint = {}

local ROOT = "TGSRR/Runs"
local FORMAT = 1

local activeRun = nil
local activePlayer = nil

local function path(runId, slot)
    return ROOT .. "/" .. tostring(runId)
        .. "/clock-" .. tostring(slot) .. ".checkpoint"
end

local function readSlot(runId, slot)
    local reader = getFileReader(path(runId, slot), false)
    if not reader then return nil end
    local payload = reader:readLine()
    local checksum = reader:readLine()
    local trailing = reader:readLine()
    reader:close()
    if not payload or not checksum or trailing
            or Hash.sha256(payload) ~= tostring(checksum):lower() then
        return nil
    end
    local decoded = EventCodec.decodePayload(payload)
    if type(decoded) ~= "table"
            or tonumber(decoded.format) ~= FORMAT
            or tostring(decoded.runId or "") ~= tostring(runId)
            or tonumber(decoded.slotSequence) == nil then
        return nil
    end
    decoded.slot = slot
    decoded.payload = payload
    decoded.checksum = checksum
    return decoded
end

function ClockCheckpoint.latest(runId)
    local a = readSlot(runId, "a")
    local b = readSlot(runId, "b")
    if not a then return b end
    if not b then return a end
    return tonumber(a.slotSequence) >= tonumber(b.slotSequence) and a or b
end

local function calendar(gameTime)
    return {
        year = tonumber(gameTime:getYear()) or 0,
        month = (tonumber(gameTime:getMonth()) or 0) + 1,
        day = (tonumber(gameTime:getDay()) or 0) + 1,
    }
end

function ClockCheckpoint.observe(run, player)
    local gameTime = getGameTime and getGameTime() or nil
    if not run or not player or not gameTime then
        return nil, "clock_checkpoint_unavailable"
    end
    return {
        format = FORMAT,
        runId = tostring(run.runId),
        eventSequence = math.max(0,
            math.floor(tonumber(run.eventSequence) or 0)),
        eventHash = tostring(run.eventHash or ""):lower(),
        utc = Identity.utcSeconds(),
        calendar = calendar(gameTime),
        timeOfDay = tonumber(gameTime:getTimeOfDay()) or 0,
        nightsSurvived = math.max(0,
            math.floor(tonumber(gameTime:getNightsSurvived()) or 0)),
        worldAgeHours = math.max(0,
            tonumber(gameTime:getWorldAgeHours()) or 0),
        playerHoursSurvived = math.max(0,
            tonumber(player:getHoursSurvived()) or 0),
    }
end

function ClockCheckpoint.write(run, player)
    local value, observeError = ClockCheckpoint.observe(run, player)
    if not value then return false, observeError end
    local previous = ClockCheckpoint.latest(run.runId)
    value.slotSequence = previous
        and math.floor(tonumber(previous.slotSequence) or 0) + 1 or 1
    local slot = previous and previous.slot == "a" and "b" or "a"
    local payload, payloadError = EventCodec.canonicalPayload(value)
    if not payload then return false, payloadError end
    local checksum = Hash.sha256(payload)
    local writer = getFileWriter(path(run.runId, slot), true, false)
    if not writer then return false, "clock_checkpoint_write_failed" end
    writer:write(payload .. "\n" .. checksum .. "\n")
    writer:close()

    local verified = readSlot(run.runId, slot)
    if not verified or verified.checksum ~= checksum
            or tonumber(verified.slotSequence) ~= value.slotSequence then
        return false, "clock_checkpoint_readback_failed"
    end
    return true, verified
end

local function onPostSave()
    if not activeRun or not activePlayer then return end
    local ok, written, result =
        pcall(ClockCheckpoint.write, activeRun, activePlayer)
    if ok and written then
        if isDebugEnabled and isDebugEnabled() then
            print("[TGSRR Clock] Saved checkpoint "
                .. tostring(result.slotSequence)
                .. " in slot " .. tostring(result.slot)
                .. " at event " .. tostring(result.eventSequence))
        end
        return
    end
    local failure = "clock_checkpoint_failed:"
        .. tostring(ok and result or written or "unknown_error")
    activeRun.integrityStatus = failure
    Recorder.deactivate()
    activeRun = nil
    activePlayer = nil
    TrackingHealth.stop(
        failure,
        "The independent clock-recovery checkpoint could not be verified."
    )
end

function ClockCheckpoint.initialize(run, player)
    activeRun = run
    activePlayer = player
    return ClockCheckpoint.latest(run.runId)
end

ClockCheckpoint.readSlot = readSlot
ClockCheckpoint.reset = function()
    activeRun = nil
    activePlayer = nil
end

Events.OnPostSave.Add(onPostSave)

return ClockCheckpoint
