local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local challenge = nil
function addChallenge(value)
    challenge = value
end

Events = {
    OnChallengeQuery = {
        Add = function(callback)
            callback()
        end,
    },
    OnGameStart = {
        Add = function() end,
    },
}

package.loaded["TGSRR/Run/SelectedChallenge"] = {
    register = function() end,
}

SandboxVars = {}
SpawnRegionMgr = {
    getSpawnRegions = function() return {} end,
}

require "LastStand/TGSRR_CDDA"
assert(challenge ~= nil)

require("TGSRR/Sandbox/Base").apply()
assert(SandboxVars.MultiplierConfig.Global == 0.8)
assert(SandboxVars.MultiplierConfig.GlobalToggle == true)
assert(SandboxVars.FirearmUseDamageChance == 2)

local function assertTablesMatch(expected, actual, prefix)
    for key, value in pairs(expected) do
        local path = prefix and (prefix .. "." .. key) or key
        assert(actual[key] ~= nil,
            "shipped TGSRR preset is missing " .. path)
        if type(value) == "table" then
            assert(type(actual[key]) == "table",
                "shipped TGSRR preset has wrong type for " .. path)
            assertTablesMatch(value, actual[key], path)
        else
            assert(actual[key] == value,
                "shipped TGSRR preset differs for " .. path)
        end
    end
end

local shippedPreset = dofile(
    sourceRoot .. "shared/Sandbox/TGSRR.lua")
assertTablesMatch(SandboxVars, shippedPreset)
assertTablesMatch(shippedPreset, SandboxVars)

challenge.OnInitWorld()
assert(SandboxVars.TimeSinceApo == 13)
assert(SandboxVars.FirearmUseDamageChance == 2)

local excluded = nil
local explosionCount = 0
local tile = {}
local selectedRoom = {
    getRandomSquare = function()
        return tile
    end,
}
local building = {
    getRandomRoomExcluding = function(_, rooms)
        excluded = rooms
        return selectedRoom
    end,
}
local room = {
    getBuilding = function()
        return building
    end,
}
local square = {
    getRoom = function()
        return room
    end,
}
local player = {
    getHoursSurvived = function() return 0 end,
    getCurrentSquare = function() return square end,
}

function getPlayer() return player end
function getCell() return {} end

ArrayList = {
    new = function()
        return {
            values = {},
            add = function(self, value)
                self.values[#self.values + 1] = value
            end,
        }
    end,
}

IsoFireManager = {
    explode = function(_, actualTile, strength)
        assert(actualTile == tile)
        assert(strength == 100000)
        explosionCount = explosionCount + 1
    end,
}

challenge.OnGameStart()
assert(explosionCount == 1)
assert(excluded.values[1] == "kitchen")
assert(excluded.values[2] == "garage")

print("cdda compatibility test passed")
