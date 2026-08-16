local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local Snapshot = require "TGSRR/Run/OutpostLifecycleSnapshot"
local stored = {
    outposts = {
        echo_creek = {
            completionCount = 2,
            regressionCount = 1,
            firstCompletion = { sequence = 2, utc = 1002 },
            latestCompletion = { utc = 1006 },
            latestRegression = { utc = 1004 },
        },
    },
    deliverables = {
        ["echo_creek\0food"] = {
            completionCount = 2,
            regressionCount = 1,
            firstCompletion = { sequence = 1, utc = 1001 },
            latestCompletion = { utc = 1005 },
            latestRegression = { utc = 1003, current = 10 },
        },
    },
}

local result = Snapshot.observe({ outpostLifecycles = stored }, {
    { body = "ledger content is deliberately irrelevant" },
})
assert(result.outposts.echo_creek.completionCount == 2)
assert(result.outposts.echo_creek.latestCompletion.sequence == nil)
assert(result.deliverables["echo_creek\0food"].regressionCount == 1)
assert(result.deliverables["echo_creek\0food"].latestRegression.current == 10)

print("outpost lifecycle snapshot test passed")
