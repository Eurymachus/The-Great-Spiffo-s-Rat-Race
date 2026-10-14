local clock, temperature, recording = 12, 0, true
local minuteCallback
local captured = {}
package.loaded["TGSRR/Run/Identity"] = {utcSeconds = function() return 1000 + clock end}
package.loaded["TGSRR/Run/TrackingHealth"] = {stop = function() end}
package.loaded["TGSRR/Run/Recorder"] = {
    isActive = function() return recording end,
    record = function(_, payload, context)
        captured[#captured + 1] = payload
        return true, context
    end,
}
Events = {
    EveryDays = {Add = function() end},
    EveryOneMinute = {Add = function(callback) minuteCallback = callback end},
}
getClimateManager = function()
    return {getTemperature = function() return temperature end}
end
getGameTime = function()
    return {
        getWorldAgeHours = function() return clock end,
        getTimeOfDay = function() return clock % 24 end,
        getYear = function() return 1993 end,
        getMonth = function() return 0 end,
        getDay = function() return math.floor(clock / 24) end,
    }
end
local player = {
    getHoursSurvived = function() return clock - 12 end,
    getZombieKills = function() return 0 end,
    getNutrition = function() return {getWeight = function() return 80 end} end,
}
for _, name in ipairs({"SkillSnapshot", "WeaponKillSnapshot", "BrokenWeaponSnapshot",
    "AnimalSlaughterSnapshot", "AnimalTrapSnapshot", "AnimalBirthSnapshot",
    "AnimalPetSnapshot", "InjurySnapshot", "MilkSnapshot", "FluidConsumedSnapshot",
    "FishCaughtSnapshot"}) do
    package.loaded["TGSRR/Run/" .. name] = {
        copy = function() return {} end, totals = function() return {} end,
        deltaPairs = function() return {} end,
    }
end
local DayTracker = require "TGSRR/Run/DayTracker"
local Tracker = require "TGSRR/Run/TemperatureTracker"
local Snapshot = require "TGSRR/Run/TemperatureSnapshot"
local DailySnapshot = require "TGSRR/Run/DailySnapshot"
local run = {lifecycle = "active"}
assert(DayTracker.initialize(run, player))
Tracker.initialize(run, true)
assert(run.outdoorTemperature.minimum.celsius == 0)
clock, temperature = 13, -13.7
minuteCallback()
clock, temperature = 14, 32.5
minuteCallback()
clock = 15
minuteCallback()
assert(run.outdoorTemperature.maximum.worldAgeHours == 14)
assert(run.outdoorTemperature.minimum.calendar.day == 1)
local active = DailySnapshot.active(run, player)
active.outdoorTemperature.minimum.calendar.day = 99
assert(run.dailyState.outdoorTemperature.minimum.calendar.day == 1)
assert(DayTracker.initialize(run, player))
Tracker.initialize(run, false)
assert(not run.outdoorTemperature.partial)
assert(run.outdoorTemperature.minimum.celsius == -13.7)

clock, temperature = 24, 8
assert(DayTracker.onNewDay())
minuteCallback()
local sealed = captured[2].completedDay.outdoorTemperature
assert(sealed.minimum.celsius == -13.7 and sealed.maximum.celsius == 32.5)
assert(run.dailyState.outdoorTemperature.minimum.celsius == 8)
assert(run.dailyState.outdoorTemperature.minimum.calendar.day == 2)
assert(run.outdoorTemperature.minimum.celsius == -13.7)
clock, temperature = 25, -20
minuteCallback()
assert(sealed.minimum.celsius == -13.7)
assert(run.outdoorTemperature.minimum.worldAgeHours == 25)
recording, temperature = false, -50
minuteCallback()
assert(run.outdoorTemperature.minimum.celsius == -20)
recording, run.lifecycle = true, "deceased"
minuteCallback()
assert(run.outdoorTemperature.minimum.celsius == -20)

local existing = {lifecycle = "active", dailyState = {}}
Tracker.initialize(existing, false)
assert(existing.outdoorTemperature.partial)
assert(existing.dailyState.outdoorTemperature.partial)
assert(Snapshot.copy(nil) == nil)
local EventCodec = require "TGSRR/Run/EventCodec"
local ExportCodec = require "TGSRR/Run/ExportCodec"
local record = assert(EventCodec.encode({runId = "temperature-test", sequence = 1,
    utc = 1024, worldAgeHours = 24, eventType = "day.started",
    payload = captured[2]}, EventCodec.GENESIS_HASH))
local projection = {outdoorTemperature = Snapshot.copy(run.outdoorTemperature),
    activeDay = DailySnapshot.active(run, player)}
local encoded = assert(ExportCodec.encode("temperature-test", 1025,
    {record}, record.hash, projection))
local decoded = assert(ExportCodec.decode(encoded))
assert(decoded.projection.outdoorTemperature.minimum.celsius == -20)
assert(decoded.projection.activeDay.outdoorTemperature.maximum.celsius == 8)
assert(decoded.projection.outdoorTemperature.minimum.worldAgeHours == 25)
local event = assert(EventCodec.inspectBody(decoded.bodies[1]))
local payload = assert(EventCodec.decodePayload(event.canonicalPayload))
assert(payload.completedDay.outdoorTemperature.minimum.celsius == -13.7)
assert(payload.completedDay.outdoorTemperature.maximum.timeOfDay == 14)
temperature = 0 / 0
local valid, failure = pcall(minuteCallback)
assert(not valid and tostring(failure):find("invalid_outdoor_temperature", 1, true))
assert(existing.outdoorTemperature.minimum.celsius == -50)
assert(existing.integrityStatus == "invalid_outdoor_temperature")
temperature = 40
local bootstrapped = {lifecycle = "active", bootstrapped = true, dailyState = {}}
Tracker.initialize(bootstrapped, true)
assert(bootstrapped.outdoorTemperature.partial)
assert(bootstrapped.outdoorTemperature.minimum.celsius == 40)
assert(ExportCodec.selfTest())
print("temperature collection, rollover, resume, partial history and export tests passed")
