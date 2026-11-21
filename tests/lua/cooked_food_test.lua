local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
package.loaded["TimedActions/ISTransferAction"] = true
package.loaded["TimedActions/ISGrabItemAction"] = true
local function list(values)
    return {size = function() return #values end, get = function(_, i) return values[i+1] end}
end
local function container(owned)
    return {owned = owned, values = {}, isInCharacterInventory = function(self) return self.owned end,
        getItems = function(self) return list(self.values) end}
end
local inv, outside, bag = container(true), container(false), container(true)
local player = {getInventory = function() return inv end}
local other = {}
local run = {runId = "run1", lifecycle = "active"}
local recording = true
package.loaded["TGSRR/Run/Recorder"] = {getActiveRun = function() return run end,
    isActive = function() return recording end}
ItemTag = {ALREADY_COOKED = {}}
function isClient() return false end
function isServer() return false end
function instanceof(item, kind) return item.kind == kind end
local function food(id, cooked, burnt)
    return {kind = "Food", data = {}, container = outside,
        getFullType = function() return id end, isCooked = function() return cooked end,
        isBurnt = function() return burnt end, hasTag = function(self) return self.already end,
        getModData = function(self) return self.data end,
        getContainer = function(self) return self.container end}
end
ISTransferAction = {transferItem = function(_, character, item, source, dest)
    if item.fail then error("transfer failed") end
    if not item.cancel then item.container = dest end
    return item
end}
ISGrabItemAction = {transferItem = function(action)
    action.item:getItem().container = action.destContainer
end}
local tracker = require("TGSRR/Run/CookedFoodTracker")
local existing = food("Base.Steak", true)
inv.values = {existing}
tracker.initialize(run, player, false)
assert(run.cookedFood.partial and not run.cookedFood.items["Base.Steak"])
local function move(item, dest, character)
    return ISTransferAction:transferItem(character or player, item, item.container, dest)
end
move(existing, inv)
assert(not run.cookedFood.items["Base.Steak"])
local steak = food("Base.Steak", true)
move(steak, inv)
assert(run.cookedFood.items["Base.Steak"] == 1)
move(steak, outside); move(steak, inv); move(steak, bag)
assert(run.cookedFood.items["Base.Steak"] == 1)
tracker.initialize(run, player, false)
-- Simulate a newly loaded item object retaining serialized ModData.
local loaded = food("Base.Steak", true); loaded.data = steak.data
move(loaded, inv)
assert(run.cookedFood.items["Base.Steak"] == 1)
local raw, burnt = food("Base.Raw", false), food("Base.Burnt", true, true)
move(raw, inv); move(burnt, inv)
assert(not run.cookedFood.items["Base.Raw"] and not run.cookedFood.items["Base.Burnt"])
local toast = food("Base.Toast", false); toast.already = true
move(toast, inv); assert(run.cookedFood.items["Base.Toast"] == 1)
local cancelled = food("Base.Cancelled", true); cancelled.cancel = true
move(cancelled, inv); assert(not run.cookedFood.items["Base.Cancelled"])
local failed = food("Base.Failed", true); failed.fail = true
assert(not pcall(move, failed, inv)); assert(not failed.data.TGSRRCookedFoodRunId)
local ground = food("Base.Chicken", true)
ISGrabItemAction.transferItem({character = player, item = {getItem = function() return ground end}, destContainer = inv})
assert(run.cookedFood.items["Base.Chicken"] == 1)
local contents = container(false); contents.values = {food("Base.Steak", true), food("Base.Steak", true)}
local sack = {kind = "InventoryContainer", container = outside, getInventory = function() return contents end,
    getContainer = function(self) return self.container end}
move(sack, inv); move(sack, outside); move(sack, inv)
assert(run.cookedFood.items["Base.Steak"] == 3)
recording = false
local paused = food("Base.Paused", true); move(paused, inv)
assert(not paused.data.TGSRRCookedFoodRunId)
recording = true
local foreign = food("Base.Foreign", true); move(foreign, inv, other)
assert(not foreign.data.TGSRRCookedFoodRunId)
run.lifecycle = "deceased"
local dead = food("Base.Dead", true); move(dead, inv)
assert(not dead.data.TGSRRCookedFoodRunId)
print("cooked food collection checks passed")

-- Exercise actual daily snapshot and rollover code with unrelated families stubbed.
for _, name in ipairs({"SkillSnapshot", "WeaponKillSnapshot", "BrokenWeaponSnapshot",
    "AnimalSlaughterSnapshot", "AnimalTrapSnapshot", "AnimalBirthSnapshot",
    "AnimalPetSnapshot", "InjurySnapshot", "MilkSnapshot", "FluidConsumedSnapshot", "FishCaughtSnapshot"}) do
    package.loaded["TGSRR/Run/" .. name] = {
        copy = function() return {} end, totals = function() return {} end,
        deltaPairs = function() return {} end,
    }
end
Events = {EveryDays = {Add = function() end}}

run.lifecycle = "active"
local age = 1
local events = {}
function getGameTime() return {getWorldAgeHours = function() return age end,
    getYear = function() return 1993 end, getMonth = function() return 6 end,
    getDay = function() return age < 24 and 9 or 10 end} end
player.getZombieKills = function() return 0 end
player.getHoursSurvived = function() return age end
package.loaded["TGSRR/Run/Identity"] = {utcSeconds = function() return 100 end}
package.loaded["TGSRR/Run/Recorder"].record = function(kind, payload)
    events[#events+1] = payload
    return true, {utc = 100, worldAgeHours = age}
end
local Daily = require("TGSRR/Run/DailySnapshot")
local Days = require("TGSRR/Run/DayTracker")
assert(Days.initialize(run, player))
move(food("Base.Steak", true), inv)
assert(Daily.active(run, player).cookedFoodItemsDeltas["Base.Steak"] == 1)
age = 25
assert(Days.onNewDay())
assert(events[#events].completedDay.cookedFoodItemsDeltas["Base.Steak"] == 1)
assert(not Daily.active(run, player).cookedFoodItemsDeltas["Base.Steak"])
tracker.initialize(run, player, false)
assert(run.cookedFood.items["Base.Steak"] == 4)
move(food("Base.Steak", true), inv)
assert(Daily.active(run, player).cookedFoodItemsDeltas["Base.Steak"] == 1)
assert(run.cookedFood.items["Base.Steak"] == 5)
print("cooked food cumulative, daily rollover and reload checks passed")
