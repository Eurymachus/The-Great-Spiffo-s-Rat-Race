local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
local now, recording, multiplier = 1000, true, 1
local events, captured = {}, {}
Events = {OnTick = {Add = function(f) events.tick = f end}, EveryDays = {Add = function() end}}
function getTimestampMs() return now end
function getGameTime() return {getMultiplier = function() return multiplier end,
 getWorldAgeHours = function() return 1 end, getYear = function() return 1993 end,
 getMonth = function() return 6 end, getDay = function() return 9 end} end
package.loaded["TGSRR/Run/Recorder"] = {isActive = function() return recording end,
 record = function(kind, payload) captured[#captured+1] = payload; return true, {utc=100,worldAgeHours=1} end}
package.loaded["TGSRR/Run/Identity"] = {utcSeconds = function() return 100 end}
local x, y, vehicle, driver = 0, 0, nil, true
local car = {isDriver = function() return driver end}
local player = {getX = function() return x end, getY = function() return y end,
 getVehicle = function() return vehicle end, getZombieKills = function() return 0 end,
 getHoursSurvived = function() return 0 end}
local Tracker = require("TGSRR/Run/DistanceTracker")
local run = {lifecycle="active", distanceTravelledMeters=0, distanceRejectedSamples=0}
Tracker.initialize(run, player, true)
local function move(dx, dy, ms) x=x+dx; y=y+dy; now=now+(ms or 100); events.tick() end
move(3,4); assert(run.distanceByModeMeters.onFoot == 5)
vehicle=car; move(2,0); assert(run.distanceTravelledMeters == 5)
move(6,0); assert(run.distanceByModeMeters.driver == 6)
driver=false; move(2,0); move(0,6); assert(run.distanceTravelledMeters == 11 and run.distanceByModeMeters.passenger == nil)
vehicle=nil; move(2,0); move(3,4); assert(run.distanceByModeMeters.onFoot == 10)
move(1000,0); assert(run.distanceRejectedSamples == 1)
move(3,4); assert(run.distanceByModeMeters.onFoot == 15)
local total=run.distanceTravelledMeters
move(0,0); assert(run.distanceTravelledMeters == total)
x=x+500; Tracker.initialize(run, player, false); move(3,4)
assert(run.distanceTravelledMeters == total+5 and not run.distanceModesPartial)
recording=false; move(3,4); recording=true
run.lifecycle="deceased"; move(3,4); assert(run.distanceTravelledMeters == total+5)
run.lifecycle="active"; move(3,4,2000); assert(run.distanceTravelledMeters == total+5)
multiplier=10; move(20,0); assert(run.distanceTravelledMeters == total+25)
assert(run.distanceTravelledMeters == run.distanceByModeMeters.onFoot + run.distanceByModeMeters.driver)
for _, name in ipairs({"SkillSnapshot", "WeaponKillSnapshot", "BrokenWeaponSnapshot",
 "AnimalSlaughterSnapshot", "AnimalTrapSnapshot", "AnimalBirthSnapshot", "AnimalPetSnapshot",
 "InjurySnapshot", "MilkSnapshot", "FluidConsumedSnapshot", "FishCaughtSnapshot"}) do
 package.loaded["TGSRR/Run/"..name] = {copy=function() return {} end,
 totals=function() return {} end, deltaPairs=function() return {} end}
end
local Daily = require("TGSRR/Run/DailySnapshot")
local Days = require("TGSRR/Run/DayTracker")
assert(Days.initialize(run,player)); move(3,4)
assert(Daily.active(run,player).distanceByModeDeltas.onFoot == 5)
assert(Days.onNewDay()); assert(captured[#captured].completedDay.distanceByModeDeltas.onFoot == 5)
assert(Daily.active(run,player).distanceByModeDeltas.onFoot == 0)
local legacy={lifecycle="active",distanceTravelledMeters=100,distanceRejectedSamples=0,dailyState={}}
Tracker.initialize(legacy,player,false); move(3,4)
assert(legacy.distanceTravelledMeters == 105 and legacy.distanceByModeMeters.onFoot == 5)
assert(legacy.distanceModesPartial and legacy.dailyState.distanceModesPartial)
Tracker.reset(); move(3,4); assert(legacy.distanceTravelledMeters == 105)
local codec=require("TGSRR/Run/ExportCodec")
local projection={schema=1,currentKills=0,character={current={displayName="Test"}},distance={travelledMeters=105,
 byModeMeters=legacy.distanceByModeMeters,modesPartial=true}, activeDay={dayIndex=1,
 distanceDeltaMeters=5,distanceByModeDeltas={onFoot=5,driver=0},distanceModesPartial=true}}
local EventCodec=require("TGSRR/Run/EventCodec")
local record=assert(EventCodec.encode({runId="distance-test",sequence=1,utc=100,
 worldAgeHours=1,eventType="run.started",payload={test=true}}))
local encoded=assert(codec.encode("distance-test",110,{record},record.hash,projection))
local decoded=assert(codec.decode(encoded))
assert(decoded.projection.distance.byModeMeters.onFoot == 5)
assert(decoded.projection.distance.byModeMeters.driver == 0)
local f=assert(io.open("outputs/distance-test.export.txt","w")); f:write(encoded); f:close()
print("distance collector, lifecycle, transition, reload and daily tests passed")
