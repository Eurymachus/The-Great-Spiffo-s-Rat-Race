local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;" .. package.path

local NEVER_SPOILS = 1000000000
local contents = {
    calories = 510,
    offAgeMax = NEVER_SPOILS,
}

function contents:getCalories() return self.calories end
function contents:getOffAgeMax() return self.offAgeMax end

function instanceof(value, className)
    return value == contents and className == "Food"
end

function getScriptManager()
    return {
        FindItem = function(_, itemType)
            assert(itemType == "Base.CannedChili")
            return {
                InstanceItem = function() return contents end,
            }
        end,
    }
end

local function item(itemType)
    return {
        getFullType = function() return itemType end,
    }
end

local BoxedFood = require "TGSRR/Outposts/Checks/BoxedFood"
assert(BoxedFood.calories(
    item("Base.CannedChili_Box"), NEVER_SPOILS) == 3060)
assert(BoxedFood.calories(item("Base.NailsBox"), NEVER_SPOILS) == 0)

contents.offAgeMax = 10
assert(BoxedFood.calories(
    item("Base.CannedChili_Box"), NEVER_SPOILS) == 0)

print("boxed food test passed")
