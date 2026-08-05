local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;" .. package.path

local run = {
    runId = "rr-terminal-test",
    lifecycle = "active",
}
local recorded = {}

package.preload["TGSRR/Run/Identity"] = function()
    return {
        get = function() return run end,
        observeCharacter = function(player)
            return { forename = player.forename }
        end,
    }
end

package.preload["TGSRR/Run/Recorder"] = function()
    return {
        record = function(eventType, payload)
            recorded[#recorded + 1] = {
                eventType = eventType,
                payload = payload,
            }
            return true, {
                utc = 123,
                worldAgeHours = 45.5,
                sequence = 9,
                hash = "terminal-hash",
            }
        end,
    }
end

local TerminalState = require "TGSRR/Run/TerminalState"
local ok = assert(TerminalState.markDeceased({ forename = "Spiffo" }))
assert(ok == true)
assert(#recorded == 1)
assert(recorded[1].eventType == "run.ended")
assert(recorded[1].payload.reason == "deceased")
assert(recorded[1].payload.character.forename == "Spiffo")
assert(run.lifecycle == "deceased")
assert(run.endedReason == "deceased")
assert(run.endedUtc == 123)
assert(run.endedWorldAgeHours == 45.5)
assert(run.endedEventSequence == 9)
assert(run.endedEventHash == "terminal-hash")

local repeated, repeatedResult = TerminalState.markDeceased({
    forename = "Spiffo",
})
assert(repeated == true)
assert(repeatedResult == "already_deceased")
assert(#recorded == 1)

print("terminal state test passed")
