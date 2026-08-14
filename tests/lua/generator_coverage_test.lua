local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;" .. package.path

local radius = 20
IsoGenerator = {
    isPoweringSquare = function(gx, gy, gz, x, y, z)
        return math.abs(z - gz) <= 3
            and ((x - gx) * (x - gx) + (y - gy) * (y - gy))
                <= radius * radius
    end,
}

local function generator(x, y, z)
    local square = {
        getX = function() return x end,
        getY = function() return y end,
        getZ = function() return z end,
    }
    return { getSquare = function() return square end }
end

local outpost = {
    coreZone = { minX = 100, minY = 100, maxX = 110, maxY = 110 },
    sealingLevel = 0,
}

local Coverage = require "TGSRR/Outposts/Checks/GeneratorCoverage"
assert(Coverage.covers(outpost, generator(90, 105, 0)) == true)
assert(Coverage.covers(outpost, generator(79, 105, 0)) == false)
assert(Coverage.covers(outpost, generator(90, 105, 3)) == true)
assert(Coverage.covers(outpost, generator(90, 105, 4)) == false)

print("generator coverage test passed")
