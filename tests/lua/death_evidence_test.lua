local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
assert(loadfile(root .. "client/TGSRR/Run/Runtime.lua"))
assert(loadfile(root .. "client/TGSRR/Run/Exporter.lua"))
local now, callback, update = 100000, nil, nil
local dead, hypo, thermal = false, 0, 0
MoodleType = {HYPOTHERMIA="hypothermia"}
function getTimestampMs() return now end
function getTimestamp() return math.floor(now / 1000) end
function getGameTime() return { getWorldAgeHours = function() return 12 end } end
Events = { OnPlayerGetDamage = { Add = function(fn) callback = fn end },
    OnPlayerUpdate = {Add = function(fn) update = fn end} }
package.preload["TGSRR/Run/StartingLocation"] = function()
    return { observe = function(player, utc, age, partial)
        return { x = math.floor(player:getX()), y = math.floor(player:getY()),
            z = math.floor(player:getZ()), buildingId = "", capturedUtc = utc,
            worldAgeHours = age, partial = partial }
    end }
end
CharacterStat = {FOOD_SICKNESS="food", POISON="poison", INTOXICATION="intoxication"}
local pills, intoxication = 0, 0
local food, poison, corpse, wound = 75, 12, 0.01, 4
local player = {
    getAttackedBy = function() return nil end,
    getSleepingPillsTaken = function() return pills end,
    isDead = function() return dead end,
    getMoodles = function() return {getMoodleLevel = function() return hypo end} end,
    getStats = function() return {get=function(_, stat)
        if stat == "intoxication" then return intoxication end
        return stat == "food" and food or poison
    end} end,
    getCorpseSicknessRate = function() return corpse end,
    getBodyDamage = function(self)
        return { getBodyParts = function() return {size=function() return 0 end} end,
            isInfected = function() return self.infected == true end,
            getGeneralWoundInfectionLevel = function() return wound end,
            getColdDamageStage = function() return thermal end }
    end,
    getX = function() return 12.8 end, getY = function() return -1.2 end,
    getZ = function() return 0 end,
    isKilledByFall = function(self) return self.fall == true end,
    isDeathDragDown = function(self) return self.drag == true end,
}
local run = { runId = "test-death", lifecycle = "active" }
local Evidence = require("TGSRR/Run/DeathEvidence")
Evidence.initialize(run, player)
assert(callback and update)
pills, intoxication = 12, 15
local medication = Evidence.capture(player, "death_callback")
assert(medication.medication.sleepingPillsTaken == 12)
assert(medication.medication.intoxication == 15 and medication.cause == "sleeping_pills")
assert(medication.schema == 4 and medication.certainty == "fatal_threshold")
for _, count in ipairs({0, 9, 10, 11}) do
    pills = count
    assert(Evidence.capture(player, "death_callback").cause == "unknown")
end
pills, intoxication = 13, 0
player.infected = true
assert(Evidence.capture(player, "death_callback").cause == "sleeping_pills")
player.infected = false
player.fall = true
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
player.drag = true
assert(Evidence.capture(player, "death_callback").certainty == "conflicting_flags")
player.fall = false
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
player.drag = false
thermal = 1 -- A terminal thermal threshold competes even without a fresh cold sample.
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
thermal = nil
assert(Evidence.capture(player, "death_callback").cause == "unknown")
thermal = 0
callback(player, "BLEEDING", 0.1)
local mixed = Evidence.capture(player, "death_callback")
assert(mixed.cause == "mixed" and mixed.certainty == "competing_evidence")
assert(mixed.lastDamageSource == "BLEEDING" and #mixed.recentDamage == 1)
pills = 11
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
pills = 10
callback(player, "THIRST", 0.1)
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
pills = 9
assert(Evidence.capture(player, "death_callback").cause == "THIRST")
pills = 10
now = now + 10000
assert(Evidence.capture(player, "death_callback").cause == "mixed")
now = now + 1
assert(Evidence.capture(player, "death_callback").cause == "unknown")
now = now - 10001
Evidence.initialize(run, player)
assert(Evidence.capture(player, "recovery").medication == nil)
pills, intoxication = 0, 0
assert(Evidence.capture(player, "death_callback").medication.sleepingPillsTaken == 0)
assert(medication.medication.sleepingPillsTaken == 12)
hypo, thermal = 4, 0.9
update(player)
now = now + 25
dead, hypo, thermal = true, 0, 1
update(player) -- Death-cleared moodles must not replace the living sample.
local frozen = Evidence.capture(player, "death_callback")
assert(frozen.lastLivingThermal.hypothermiaLevel == 4)
assert(frozen.lastLivingThermal.damageStage == 0.9)
assert(frozen.lastLivingThermal.ageMilliseconds == 25)
assert(frozen.lastLivingThermal.observedUtc == 100)
assert(frozen.thermalDamageStageAtDeath == 1 and frozen.cause == "hypothermia" and frozen.certainty == "fatal_threshold")
assert(Evidence.capture(player, "recovery").lastLivingThermal == nil)
thermal = 0.99
assert(Evidence.capture(player, "death_callback").cause == "unknown")
thermal = 1
now = now + 1000
assert(Evidence.capture(player, "death_callback").cause == "unknown")
now = now - 1000
player.fall = true
assert(Evidence.capture(player, "death_callback").cause == "fall")
player.fall = false
callback(player, "BLEEDING", 0.1)
assert(Evidence.capture(player, "death_callback").cause == "BLEEDING")
dead, hypo, thermal = false, 0, 0
update(player) -- Genuine recovery must overwrite the previous level.
assert(Evidence.capture(player, "death_callback").lastLivingThermal.hypothermiaLevel == 0)
hypo=4; update({})
assert(Evidence.capture(player, "death_callback").lastLivingThermal.hypothermiaLevel == 0)
now = now - 100
assert(Evidence.capture(player, "death_callback").lastLivingThermal == nil)
now = now + 100
Evidence.initialize(run, player)
assert(frozen.lastLivingThermal.hypothermiaLevel == 4)
dead=true; Evidence.initialize(run, player)
assert(Evidence.capture(player, "death_callback").lastLivingThermal == nil)
dead, hypo = false, 0; Evidence.initialize(run, player)
callback({}, "FIRE", 1) -- Other players cannot supply this run's evidence.
callback(player, "POISON", 0)
assert(Evidence.capture(player, "death_callback").cause == "unknown")
callback(player, "SICK", 1)
local sick = Evidence.capture(player, "death_callback")
assert(sick.cause == "SICK" and sick.sickness.foodSickness == 75)
callback(player, "POISON", 0.5)
callback(player, "SICK", 1)
local poisoned = Evidence.capture(player, "death_callback")
assert(poisoned.cause == "POISON" and poisoned.certainty == "suspected")
assert(poisoned.lastDamageSource == "SICK" and #poisoned.recentDamage == 2)
player.fall = true
assert(Evidence.capture(player, "death_callback").cause == "fall")
player.fall = false
callback(player, "BLEEDING", 0.1)
assert(Evidence.capture(player, "death_callback").cause == "BLEEDING")
now = now + 10001
callback(player, "SICK", 1)
assert(Evidence.capture(player, "death_callback").cause == "SICK")
assert(sick.recentDamage[1].sickness.poison == 12)
food, poison, corpse, wound = 80, 0, 0, 0
local changed = Evidence.capture(player, "death_callback")
assert(changed.sickness.poison == 0 and changed.recentDamage[1].sickness.poison == 12)
assert(changed.recentDamage[1].sickness.foodSickness == 75)
assert(Evidence.capture(player, "recovery").sickness == nil)
Evidence.initialize(run, player)
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
-- Exercise terminal collection, classification and the actual export codec together.
local oldBody = player.getBodyDamage
local bandaged, woundBleeding = false, 5
BodyPartType = {ToString=function(value) return value end}
player.getBodyDamage = function(self)
    local body = oldBody(self)
    body.getBodyParts = function() return {size=function() return 1 end, get=function()
        return {getType=function() return "ForeArm_L" end,
            getBiteTime=function() return 10 end, getScratchTime=function() return 0 end,
            getCutTime=function() return 0 end, getDeepWoundTime=function() return 0 end,
            bandaged=function() return bandaged end, getBleedingTime=function() return woundBleeding end}
    end} end
    return body
end
player.fall, player.drag, player.infected = false, false, true
dead, pills, thermal, hypo = false, 0, 0, 0
run.lifecycle = "active"
Evidence.initialize(run, player)
callback(player, "BLEEDING", 0.1)
local zombieBleeding = Evidence.capture(player, "death_callback")
assert(zombieBleeding.cause == "zombie_attack" and zombieBleeding.certainty == "suspected")
assert(zombieBleeding.lastDamageSource == "BLEEDING" and zombieBleeding.infectedAtDeath)
assert(zombieBleeding.terminalWounds[1].zombieAssociation == "bite")
bandaged = true
assert(Evidence.capture(player, "death_callback").cause == "BLEEDING")
bandaged, woundBleeding = false, 0
assert(Evidence.capture(player, "death_callback").cause == "BLEEDING")
woundBleeding, player.drag = 5, true
assert(Evidence.capture(player, "death_callback").cause == "zombie_drag_down")
pills = 10
assert(Evidence.capture(player, "death_callback").certainty == "competing_evidence")
assert(Evidence.capture(player, "recovery").terminalWounds == nil)
if arg and arg[1] then
    local file = assert(io.open(arg[1], "wb"))
    file:write(encoded)
    file:close()
end
if arg and arg[2] then
    local file = assert(io.open(arg[2], "wb"))
    file:write(EventCodec.canonicalPayload({medication, mixed, frozen, run.deathEvidence, zombieBleeding}))
    file:close()
end
print("death evidence tests passed")
