local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local subscriptions = {}
package.loaded["TGSRR/Core/Events"] = {
    subscribe = function(name, key, callback) subscriptions[name] = callback end,
}
package.loaded["TGSRR/Outposts/Completion"] = {
    calculate = function()
        return { passedRequirements = 14, totalRequirements = 14, percent = 100 }
    end,
}
package.loaded["TGSRR/Run/Identity"] = { utcSeconds = function() return 2000 end }

local run = { createdWorldAgeHours = 24 }
local recorded = {}
package.loaded["TGSRR/Run/Recorder"] = {
    getActiveRun = function() return run end,
    record = function(eventType, payload)
        recorded[#recorded + 1] = { eventType = eventType, payload = payload }
        return true, {
            sequence = #recorded,
            utc = 2000 + #recorded,
            worldAgeHours = 48 + #recorded,
        }
    end,
}
getGameTime = function()
    return { getWorldAgeHours = function() return 50 end }
end

require("TGSRR/Run/EventBridge").install()
local event = {
    outpostId = "rosewood",
    deliverableId = "engine_start",
    current = { current = 1, required = 1, state = "started" },
}
subscriptions["outpost.deliverable.completed"](event)
subscriptions["outpost.deliverable.regressed"](event)
subscriptions["outpost.deliverable.completed"](event)
subscriptions["outpost.deliverable.regressed"](event)

assert(#recorded == 1)
assert(recorded[1].eventType == "outpost.deliverable.completed")
local lifecycle = run.outpostLifecycles.deliverables[
    "rosewood\0engine_start"]
assert(lifecycle.completionCount == 2)
assert(lifecycle.regressionCount == 2)
assert(lifecycle.firstCompletion.sequence == 1)
assert(lifecycle.latestCompletion.sequence == nil)
assert(lifecycle.latestRegression.sequence == nil)

print("outpost lifecycle event bridge test passed")
