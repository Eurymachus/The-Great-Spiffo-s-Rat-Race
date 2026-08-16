local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

local records = {
    legacy_default = {
        discovered = false,
        deliverables = {
            food = {
                available = false,
                passed = false,
                current = 0,
                required = 0,
                observedAt = 0,
            },
        },
    },
    observed = {
        discovered = true,
        discoveredAt = 2,
        deliverables = {
            food = {
                available = true,
                passed = false,
                current = 0,
                required = 5000,
                observedAt = 2,
            },
            generator = {
                available = false,
                passed = false,
                current = 0,
                required = 0,
            },
        },
    },
    lifecycle_only = {
        discovered = false,
        deliverables = {},
    },
}

package.loaded["TGSRR/Outposts/Definitions"] = {
    getAll = function()
        return {
            { id = "legacy_default" },
            { id = "observed" },
            { id = "lifecycle_only" },
        }
    end,
}
package.loaded["TGSRR/Outposts/ProgressStore"] = {
    get = function(id) return records[id] end,
}
package.loaded["TGSRR/Outposts/Completion"] = {
    getDeliverableIds = function() return { "food", "generator" } end,
    calculate = function()
        return {
            complete = false,
            progress = 0,
            passedRequirements = 0,
            totalRequirements = 2,
            fractions = { food = 0, generator = 0 },
        }
    end,
}

local Snapshot = require "TGSRR/Run/OutpostSnapshot"
local result = Snapshot.observe({
    outposts = {},
    deliverables = {
        ["lifecycle_only\0food"] = {
            completionCount = 1,
            firstCompletion = { sequence = 1 },
        },
    },
})

assert(#result == 1)
assert(result[1].id == "observed")
assert(#result[1].deliverables == 1)
assert(result[1].deliverables[1].id == "food")

print("outpost snapshot test passed")
