local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local recorded = nil
local updateHandler = nil

package.loaded["TGSRR/Locations/Definitions"] = {
    getVersion = function() return 1 end,
    getAll = function()
        return { { id = "test_landmark" } }
    end,
    findByBuildingId = function(id)
        if id == "9007199254740993123" then
            return { id = "test_landmark", name = "Test Landmark" }
        end
    end,
    findAt = function() return nil end,
}

package.loaded["TGSRR/Run/Recorder"] = {
    record = function(eventType, payload)
        recorded = { eventType = eventType, payload = payload }
        return true, { utc = 123, worldAgeHours = 45.5 }
    end,
}

Events = {
    OnPlayerUpdate = {
        Add = function(callback) updateHandler = callback end,
    },
}

function getTimestampMs() return 1000 end
function isDebugEnabled() return false end

local buildingDef = {
    getIDString = function() return "9007199254740993123" end,
}
local building = {
    getDef = function() return buildingDef end,
}
local square = {
    getBuilding = function() return building end,
}
local player = {
    getCurrentSquare = function() return square end,
    getX = function() return 101.75 end,
    getY = function() return 202.25 end,
    getZ = function() return 0 end,
}
local run = {}

local Tracker = require "TGSRR/Run/LocationTracker"
assert(type(updateHandler) == "function")
Tracker.initialize(run, player, true)

assert(recorded and recorded.eventType == "location.visited")
assert(recorded.payload.locationId == "test_landmark")
assert(recorded.payload.buildingId == "9007199254740993123")
assert(recorded.payload.discoveryMethod == "building")
assert(run.locations.visits.test_landmark.buildingId
    == "9007199254740993123")
assert(run.locations.visits.test_landmark.x == 101)
assert(run.locations.visits.test_landmark.y == 202)
assert(run.buildingVisits["9007199254740993123"].x == 101)
assert(run.buildingVisits["9007199254740993123"].y == 202)
assert(run.buildingVisits["9007199254740993123"].z == 0)

recorded = nil
updateHandler(player)
assert(recorded == nil)

print("landmark tracker test passed")
