package.path = package.path
    .. ";Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/shared/?.lua"

local StartingLocation = require "TGSRR/Run/StartingLocation"

local buildingId = "10835,10144,0"
local player = {
    getX = function() return 10835.75 end,
    getY = function() return 10144.25 end,
    getZ = function() return 0 end,
    getSquare = function()
        return {
            getBuilding = function()
                return {
                    getDef = function()
                        return { getIDString = function() return buildingId end }
                    end,
                }
            end,
        }
    end,
}

local location = StartingLocation.observe(player, 1784800000, 0.5, false)
assert(location.x == 10835)
assert(location.y == 10144)
assert(location.z == 0)
assert(location.buildingId == buildingId)
assert(location.registeredLocation == nil)
assert(location.capturedUtc == 1784800000)
assert(location.worldAgeHours == 0.5)
assert(location.partial == false)

buildingId = "6192677120901126"
local landmark = StartingLocation.observe(player, 1, 2, true)
assert(landmark.registeredLocation.kind == "landmark")
assert(landmark.registeredLocation.id == "star_eplex_cinema")
assert(landmark.registeredLocation.registryVersion == 1)
assert(landmark.partial == true)

print("starting_location_test: ok")
