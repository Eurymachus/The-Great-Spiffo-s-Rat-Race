local payloads = {}
local payloadSequence = 0
local files = {}

package.loaded["TGSRR/Run/EventCodec"] = {
    canonicalPayload = function(value)
        payloadSequence = payloadSequence + 1
        local key = "payload-" .. tostring(payloadSequence)
        payloads[key] = value
        return key
    end,
    decodePayload = function(value)
        return payloads[value]
    end,
}
package.loaded["TGSRR/Run/Hash"] = {
    sha256 = function(value) return "hash-" .. tostring(value) end,
}
package.loaded["TGSRR/Run/Identity"] = {
    utcSeconds = function() return 1234 end,
}
package.loaded["TGSRR/Run/Recorder"] = {
    deactivate = function() end,
}
package.loaded["TGSRR/Run/TrackingHealth"] = {
    stop = function() end,
}

Events = {
    OnPostSave = { Add = function() end },
}

function getFileWriter(path)
    local content = ""
    return {
        write = function(_, value) content = content .. value end,
        close = function() files[path] = content end,
    }
end

function getFileReader(path)
    local content = files[path]
    if not content then return nil end
    local lines = {}
    for line in content:gmatch("([^\n]*)\n") do
        lines[#lines + 1] = line
    end
    local cursor = 0
    return {
        readLine = function()
            cursor = cursor + 1
            return lines[cursor]
        end,
        close = function() end,
    }
end

local clock = {
    year = 1993,
    month = 1,
    day = 10,
    timeOfDay = 13,
    nightsSurvived = 4,
}
local gameTime = {
    getYear = function() return clock.year end,
    getMonth = function() return clock.month - 1 end,
    getDay = function() return clock.day - 1 end,
    getTimeOfDay = function() return clock.timeOfDay end,
    getNightsSurvived = function() return clock.nightsSurvived end,
    getWorldAgeHours = function() return 102 end,
}
function getGameTime() return gameTime end

local player = {
    getHoursSurvived = function() return 56 end,
}
local run = {
    runId = "rr-clock-test",
    eventSequence = 20,
    eventHash = "abc",
}

local ClockCheckpoint = require "TGSRR/Run/ClockCheckpoint"

local firstOk, first = ClockCheckpoint.write(run, player)
assert(firstOk)
assert(first.slot == "a")
assert(first.slotSequence == 1)

run.eventSequence = 21
run.eventHash = "def"
local secondOk, second = ClockCheckpoint.write(run, player)
assert(secondOk)
assert(second.slot == "b")
assert(second.slotSequence == 2)
assert(ClockCheckpoint.latest(run.runId).eventSequence == 21)

files["TGSRR/Runs/rr-clock-test/clock-b.checkpoint"] = "truncated\n"
local recovered = ClockCheckpoint.latest(run.runId)
assert(recovered.slot == "a")
assert(recovered.slotSequence == 1)
assert(recovered.eventSequence == 20)

print("clock checkpoint test passed")
