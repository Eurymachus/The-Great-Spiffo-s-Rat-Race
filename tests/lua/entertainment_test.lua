local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
local game = "C:/Games/Steam/steamapps/common/ProjectZomboid/media/lua/shared/TimedActions/ISReadABook.lua"
ISBaseTimedAction = {
    derive = function() return {} end,
    perform = function() end, stop = function() end,
}
package.loaded["TimedActions/ISBaseTimedAction"] = true
assert(loadfile(game))()
package.loaded["TimedActions/ISReadABook"] = true
SkillBook = { Woodwork = {} }
local server, client, recording = false, false, true
function isServer() return server end
function isClient() return client end
function sendServerCommand() end
function sendSyncPlayerFields() end
function syncItemFields() end
local age = 1
local gameTime = {getWorldAgeHours = function() return age end,
    getYear = function() return 1993 end, getMonth = function() return 6 end,
    getDay = function() return 9 end}
function getGameTime() return gameTime end
local run = {lifecycle = "active"}
local events = {}
package.loaded["TGSRR/Run/Identity"] = {utcSeconds = function() return 100 end}
package.loaded["TGSRR/Run/Recorder"] = {
    getActiveRun = function() return run end,
    isActive = function() return recording end,
    record = function(kind, payload)
        events[#events + 1] = payload
        return true, {utc = 100, worldAgeHours = age}
    end,
}
local player = {
    getOnlineID = function() return 0 end,
    getAlreadyReadBook = function() return {add = function() end} end,
    learnRecipe = function() end,
    setReading = function() end, playSound = function() end,
    ReadLiterature = function(_, item)
        if item.fail then error("vanilla_failure") end
        item.consumed = item.id == "Base.MagazineCrossword" or item.id == "Base.MagazineWordsearch"
    end,
    getZombieKills = function() return 0 end, getHoursSurvived = function() return age end,
}
local function item(id, options)
    local value = options or {}
    value.id = id
    value.getID = function() return 1 end
    value.getFullType = function(self) return self.id end
    value.getType = function(self) return self.id:sub(6) end
    value.getSkillTrained = function(self) return self.skill end
    value.getLearnedRecipes = function(self) return self.recipes end
    value.hasModData = function(self) return self.data ~= nil end
    value.getModData = function(self) return self.data end
    value.setJobDelta = function() end
    value.setAlreadyReadPages = function() end
    value.getAlreadyReadPages = function() return -1 end
    value.getNumberOfPages = function() return -1 end
    value.getContainer = function() return {setDrawDirty = function() end} end
    return value
end
local function action(value, character)
    return setmetatable({item = value, character = character or player}, {__index = ISReadABook})
end
local Tracker = require("TGSRR/Run/EntertainmentTracker")
local Snapshot = require("TGSRR/Run/EntertainmentSnapshot")
Tracker.initialize(run, player, true)
assert(not run.entertainment.partial)
local read = action(item("Base.Book_Art"))
read:perform()
assert(run.entertainment.literature["Base.Book_Art"] == nil)
assert(read:complete())
read:complete() -- Duplicate completion callback is not a second reading action.
assert(run.entertainment.literature["Base.Book_Art"] == 1)
action(read.item):complete() -- A fresh action rereading the same item counts.
assert(run.entertainment.literature["Base.Book_Art"] == 2)
-- A mod adding recipes to an otherwise eligible type must not earn leisure credit.
action(item("Base.Book_Art", {recipes = {
    isEmpty = function() return false end, contains = function() return false end,
}})):complete()
action(item("Base.Book_Art", {data = {learnedRecipe = "Mod.Recipe"}})):complete()
assert(run.entertainment.literature["Base.Book_Art"] == 2)
local interrupted = action(item("Base.ComicBook"))
interrupted:stop()
assert(run.entertainment.literature["Base.ComicBook"] == nil)
for _, id in ipairs({"Base.Paperback_Art", "Base.ComicBook", "Base.Magazine", "Base.MagazineCrossword", "Base.MagazineWordsearch"}) do
    local value = item(id)
    action(value):complete()
    assert(run.entertainment.literature[id] == 1)
    if id == "Base.MagazineCrossword" or id == "Base.MagazineWordsearch" then assert(value.consumed) end
end
-- All unreviewed types remain excluded, including skill books and arbitrary prefix matches.
local mapping = require("TGSRR/Run/EntertainmentLiteratureTypes")
for _, id in ipairs({"Base.BookCarpentry1", "Base.ElectronicsMag4", "Base.Notebook", "Base.Newspaper", "Other.Book_Art"}) do
    assert(mapping[id] == nil)
end
action(item("Base.Notebook")):complete()
action(item("Base.Book_Art"), setmetatable({}, {__index = player})):complete()
server = true; action(read.item):complete(); server = false
client = true; action(read.item):complete(); client = false
recording = false; action(read.item):complete(); recording = true
run.lifecycle = "deceased"; action(read.item):complete(); run.lifecycle = "active"
assert(run.entertainment.literature["Base.Book_Art"] == 2)
local ok, err = pcall(function() action(item("Base.Book_Art", {fail = true})):complete() end)
assert(not ok and tostring(err):find("vanilla_failure"))
assert(run.entertainment.literature["Base.Book_Art"] == 2)
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
local Daily = require("TGSRR/Run/DailySnapshot")
local Days = require("TGSRR/Run/DayTracker")
assert(Days.initialize(run, player))
action(read.item):complete()
assert(Daily.active(run, player).entertainmentLiteratureDeltas["Base.Book_Art"] == 1)
age = 25
assert(Days.onNewDay())
assert(events[#events].completedDay.entertainmentLiteratureDeltas["Base.Book_Art"] == 1)
assert(Daily.active(run, player).entertainmentLiteratureDeltas["Base.Book_Art"] == nil)
Tracker.initialize(run, player, false) -- Saved counts survive reinitialization.
assert(run.entertainment.literature["Base.Book_Art"] == 3)
assert(not run.entertainment.partial)
local copy = Snapshot.observe(run)
copy.literature["Base.Book_Art"] = 999
assert(run.entertainment.literature["Base.Book_Art"] == 3)
assert(copy.schema == nil)
run = {lifecycle = "active", dailyState = {}}
assert(not pcall(function() Tracker.initialize(run, player, false) end))
run = {lifecycle = "active", entertainment = {schema = 1, literature = {}}}
assert(not pcall(function() Tracker.initialize(run, player, false) end))
run = {lifecycle = "active", bootstrapped = true}
assert(not pcall(function() Tracker.initialize(run, player, true) end))
run = {lifecycle = "active", entertainment = {literature = {["Base.Book_Art"] = 1}}}
Tracker.initialize(run, player, false) -- Restored checkpoint counters are retained.
assert(run.entertainment.literature["Base.Book_Art"] == 1)
assert(Snapshot.observe(run).partial == nil)
local Codec = require("TGSRR/Run/EventCodec")
assert(Codec.canonicalPayload({entertainment = Snapshot.observe(run)}))
print("entertainment vanilla-action, persistence and daily tests passed")
