package.loaded["TGSRR/Outposts/WorldResolver"] = {}
GridSquareEdgeFacingDirection = { NORTH_SOUTH = {}, EAST_WEST = {} }
function instanceof() return false end

local northDoor = { IsOpen = function() return false end }
local westDoor = { IsOpen = function() return true end }
local wall = { getProperties = function() return nil end }
local doors = {
    [GridSquareEdgeFacingDirection.NORTH_SOUTH] = northDoor,
    [GridSquareEdgeFacingDirection.EAST_WEST] = westDoor,
}
local walls = {}
local square = {
    getObjects = function() return { size = function() return 0 end } end,
    getDoor = function(_, facing)
        assert(facing == GridSquareEdgeFacingDirection.NORTH_SOUTH
            or facing == GridSquareEdgeFacingDirection.EAST_WEST,
            "42.21 door lookup requires the exposed direction enum")
        return doors[facing]
    end,
    getWall = function(_, north)
        assert(type(north) == "boolean", "wall lookup still requires a boolean")
        return walls[north]
    end,
}
function getCell()
    return { getGridSquare = function(_, x) return x == 0 and square or nil end }
end

local Envelope = require("TGSRR/Outposts/Checks/ExteriorEnvelope")
Envelope.get = function()
    return { segments = {
        { key = "N", x = 0, y = 0, z = 0, north = true },
        { key = "W", x = 0, y = 0, z = 0, north = false },
        { key = "missing", x = 1, y = 0, z = 0, north = true },
    } }
end
local outpost = { id = "church" }
local context = {}
local result = Envelope.inspect(outpost, context)
assert(result.available == false and result.missingSquares == 1)
assert(result.segments[1].door == northDoor and result.segments[1].doorClosed)
assert(result.segments[2].door == westDoor and not result.segments[2].doorClosed)
assert(result.segments[1].sealed and result.segments[2].sealed)
assert(Envelope.inspect(outpost, context) == result)

doors = {}
walls[true] = wall
result = Envelope.inspect(outpost, {})
assert(result.segments[1].solidWall and result.segments[1].sealed)
assert(not result.segments[2].sealed and result.segments[2].door == nil)
print("exterior envelope 42.21 test passed")
