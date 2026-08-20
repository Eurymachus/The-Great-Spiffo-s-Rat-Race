local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local values = {
    TGSRR_Run = {
        runId = "rr-old-development-run",
        schemaVersion = 22,
        eventSequence = 57,
    },
}

ModData = {
    getOrCreate = function(key)
        values[key] = values[key] or {}
        return values[key]
    end,
    remove = function(key)
        local previous = values[key]
        values[key] = nil
        return previous
    end,
}
package.loaded["TGSRR/Run/CharacterSnapshot"] = {
    identity = function() return {} end,
    traits = function() return {} end,
}

local Identity = require "TGSRR/Run/Identity"
local run, reason = Identity.get()
assert(run == nil and reason == nil)
assert(values.TGSRR_Run.schemaVersion == 23)
assert(values.TGSRR_Run.contractVersion == 1)
assert(values.TGSRR_Run.runId == nil)

local reset = assert(Identity.consumeDevelopmentReset())
assert(reset.oldRunId == "rr-old-development-run")
assert(reset.reason == "unsupported_run_schema:22")
assert(Identity.consumeDevelopmentReset() == nil)

print("development reset test passed")
