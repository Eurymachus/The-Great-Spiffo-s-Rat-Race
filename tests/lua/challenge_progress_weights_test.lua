local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

local ProgressWeights = require "TGSRR/Challenge/ProgressWeights"

local function near(actual, expected)
    assert(math.abs(actual - expected) < 0.000001,
        tostring(actual) .. " did not equal " .. tostring(expected))
end

near(ProgressWeights.calculate({
    { id = "kills", percent = 100, available = true },
    { id = "outposts", percent = 0, available = true },
    { id = "skills", percent = 0, available = true },
}), 50)

near(ProgressWeights.calculate({
    { id = "kills", percent = 40, available = true },
    { id = "outposts", percent = 80, available = true },
    { id = "skills", percent = 20, available = true },
    { id = "landmarks", percent = 100, available = true, optional = true },
}), 45)

near(ProgressWeights.calculate({
    { id = "kills", percent = 50, available = true },
    { id = "outposts", percent = 100, available = false },
    { id = "skills", percent = 100, available = false },
}), 50)

near(ProgressWeights.calculate({}), 0)

print("challenge progress weights test passed")
