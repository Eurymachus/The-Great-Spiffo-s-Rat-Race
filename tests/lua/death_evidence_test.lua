local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
assert(loadfile(root .. "client/TGSRR/Run/Runtime.lua"))
assert(loadfile(root .. "client/TGSRR/Run/Exporter.lua"))
local now, callback = 100000, nil
function getTimestampMs() return now end
function getTimestamp() return math.floor(now / 1000) end
function getGameTime() return { getWorldAgeHours = function() return 12 end } end
Events = { OnPlayerGetDamage = { Add = function(fn) callback = fn end } }
package.preload["TGSRR/Run/StartingLocation"] = function()
    return { observe = function(player, utc, age, partial)
        return { x = math.floor(player:getX()), y = math.floor(player:getY()),
            z = math.floor(player:getZ()), buildingId = "", capturedUtc = utc,
            worldAgeHours = age, partial = partial }
    end }
end
local player = {
    getBodyDamage = function(self)
        return { isInfected = function() return self.infected == true end }
    end,
    getX = function() return 12.8 end, getY = function() return -1.2 end,
    getZ = function() return 0 end,
    isKilledByFall = function(self) return self.fall == true end,
    isDeathDragDown = function(self) return self.drag == true end,
}
local run = { runId = "test-death", lifecycle = "active" }
local Evidence = require("TGSRR/Run/DeathEvidence")
Evidence.initialize(run, player)
assert(callback)
callback({}, "FIRE", 1) -- Other players cannot supply this run's evidence.
callback(player, "POISON", 0)
assert(Evidence.capture(player, "death_callback").cause == "unknown")
callback(player, "FIRE", 2)
now = now + 10
callback(player, "BLEEDING", 0.2)
callback(player, "THIRST", 0.1) -- Equal timestamps preserve event order.
local observed = Evidence.capture(player, "death_callback")
assert(observed.cause == "THIRST" and observed.certainty == "suspected")
assert(#observed.recentDamage == 3 and observed.recentDamage[1].ageMilliseconds == 10)
assert(observed.location.x == 12 and observed.location.y == -2)
assert(observed.location.partial == false)
assert(observed.infectedAtDeath == false)
player.infected = true
callback(player, "FIRE", 3) -- One latest observation per source, not a summed total.
assert(Evidence.capture(player, "death_callback").lastDamageSource == "FIRE")
player.fall = true
assert(Evidence.capture(player, "death_callback").cause == "fall")
assert(Evidence.capture(player, "death_callback").infectedAtDeath == true)
player.drag = true
assert(Evidence.capture(player, "death_callback").certainty == "conflicting_flags")
player.fall = false
assert(Evidence.capture(player, "death_callback").cause == "zombie_drag_down")
assert(Evidence.capture(player, "death_callback").infectedAtDeath == true)
player.drag = false
now = now + 10001
assert(Evidence.capture(player, "death_callback").cause == "unknown")
for index = 1, 40 do callback(player, "SOURCE" .. index, 1) end
assert(#Evidence.capture(player, "death_callback").recentDamage == 32)
local recovery = Evidence.capture(player, "recovery")
assert(#recovery.recentDamage == 0 and recovery.location.partial)
assert(recovery.infectedAtDeath == nil)
assert(Evidence.capture(nil, "recovery").location == nil)
now = now - 1000 -- Clock rollback invalidates recent ages.
assert(#Evidence.capture(player, "death_callback").recentDamage == 0)
Evidence.initialize({ lifecycle = "active" }, player)
assert(#Evidence.capture(player, "death_callback").recentDamage == 0)
Evidence.initialize(run, player)
callback(player, "INFECTION", 110)
local records, fail = {}, true
package.preload["TGSRR/Run/Identity"] = function()
    return { get = function() return run end, observeCharacter = function() return {} end }
end
package.preload["TGSRR/Run/Recorder"] = function()
    return { record = function(kind, payload)
        if fail then return false, "test_failure" end
        records[#records + 1] = payload
        return true, { utc = 100, worldAgeHours = 12, sequence = 3, hash = "hash" }
    end }
end
local Terminal = require("TGSRR/Run/TerminalState")
assert(Terminal.markDeceased(player, "death_callback") == false)
assert(run.lifecycle == "active" and run.deathEvidence == nil)
fail = false
assert(Terminal.markDeceased(player, "death_callback"))
assert(run.deathEvidence.lastDamageSource == "INFECTION")
assert(run.deathEvidence.infectedAtDeath == true)
assert(records[1].deathEvidence == run.deathEvidence)
now = now + 20000
player.fall = true
player.infected = false
assert(Terminal.markDeceased(player, "recovery"))
assert(#records == 1 and run.deathEvidence.cause == "INFECTION")
assert(run.deathEvidence.infectedAtDeath == true)
local EventCodec = require("TGSRR/Run/EventCodec")
local ExportCodec = require("TGSRR/Run/ExportCodec")
local record = assert(EventCodec.encode({ runId = run.runId, sequence = 1,
    utc = 100, worldAgeHours = 12, eventType = "run.ended", payload = records[1] }))
local projection = { schema = 1, currentKills = 0, character = { current = { displayName = "Test" } },
    lifecycle = "deceased", endedReason = "deceased", endedUtc = 100,
    endedWorldAgeHours = 12, endedEventSequence = 1, deathEvidence = run.deathEvidence }
local encoded = assert(ExportCodec.encode(run.runId, 110, { record }, record.hash, projection))
local decoded = assert(ExportCodec.decode(encoded))
assert(EventCodec.canonicalPayload(decoded.projection.deathEvidence)
    == EventCodec.canonicalPayload(run.deathEvidence))
if arg and arg[1] then
    local file = assert(io.open(arg[1], "wb"))
    file:write(encoded)
    file:close()
end
print("death evidence tests passed")
