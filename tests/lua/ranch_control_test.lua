local RanchControl = require "TGSRR/Animals/RanchControl"

local function zone(name, zoneType, x, y, z, width, height)
    local state = {
        name = name,
        type = zoneType,
        setTypeCalls = 0,
    }

    local value = {
        getName = function() return state.name end,
        getType = function() return state.type end,
        getX = function() return x end,
        getY = function() return y end,
        getZ = function() return z end,
        getWidth = function() return width end,
        getHeight = function() return height end,
        setType = function(_, newType)
            state.type = newType
            state.setTypeCalls = state.setTypeCalls + 1
        end,
    }

    return value, state
end

local chicken, chickenState = zone("chicken", "Ranch", 100, 200, 0, 20, 30)
local cow, cowState = zone("cow", "TGSRR_Ranch", 400, 500, 0, 40, 50)
local forest, forestState = zone("", "Forest", 600, 700, 0, 60, 70)
local values = { chicken, cow, forest }

local chunk = {
    getZonesSize = function() return #values end,
    getZone = function(_, index) return values[index + 1] end,
}
local cell = {
    hasChunk = function(_, x, y) return x == 0 and y == 0 end,
    getChunk = function(_, x, y)
        assert(x == 0 and y == 0)
        return chunk
    end,
}
local metaGrid = {
    getMinX = function() return -2 end,
    getMinY = function() return 3 end,
    getMaxX = function() return 4 end,
    getMaxY = function() return 8 end,
    getCellData = function(_, x, y)
        if x == -2 and y == 3 then return cell end
        return nil
    end,
    getZonesIntersecting = function()
        error("whole-world intersection must not be used")
    end,
}

local ranches = RanchControl.intercept(metaGrid)

local minX, minY, width, height = RanchControl.worldBounds(metaGrid)
assert(minX == -512)
assert(minY == 768)
assert(width == 1792)
assert(height == 1536)

local chickenKey = "100:200:0:20:30:chicken"
local cowKey = "400:500:0:40:50:cow"

assert(ranches[chickenKey].zone == chicken)
assert(ranches[chickenKey].originalName == "chicken")
assert(ranches[chickenKey].wasVanilla == true)
assert(ranches[cowKey].zone == cow)
assert(ranches[cowKey].originalName == "cow")
assert(ranches[cowKey].wasVanilla == false)
assert(ranches["600:700:0:60:70:"] == nil)

assert(chickenState.type == RanchControl.CONTROLLED_TYPE)
assert(chickenState.setTypeCalls == 1)
assert(cowState.type == RanchControl.CONTROLLED_TYPE)
assert(cowState.setTypeCalls == 0)
assert(forestState.type == "Forest")
assert(forestState.setTypeCalls == 0)

local secondPass = RanchControl.intercept(metaGrid)
assert(secondPass[chickenKey].wasVanilla == false)
assert(secondPass[cowKey].wasVanilla == false)
assert(chickenState.setTypeCalls == 1)
assert(cowState.setTypeCalls == 0)

local restored = RanchControl.restoreVanilla(metaGrid)
assert(restored == 2)
assert(chickenState.type == RanchControl.VANILLA_TYPE)
assert(cowState.type == RanchControl.VANILLA_TYPE)
assert(forestState.type == "Forest")

print("ranch control test passed")
