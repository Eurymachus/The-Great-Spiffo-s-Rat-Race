local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;" .. package.path

local gameStartHandler = nil
local dailyHandler = nil
Events = {
    OnGameStart = {
        Add = function(handler) gameStartHandler = handler end,
    },
    EveryDays = {
        Add = function(handler) dailyHandler = handler end,
    },
}

local helicopterValue = 4
local helicopterOption = {
    setValue = function(_, value) helicopterValue = value end,
}

function getSandboxOptions()
    return {
        getOptionByName = function(_, name)
            assert(name == "Helicopter")
            return helicopterOption
        end,
    }
end

SandboxVars = {
    Helicopter = 4,
}

local schedulerUpdateCount = 0
package.loaded["TGSRR/Core/HelicopterScheduler"] = {
    update = function(options)
        assert(options.replaceScheduleOnInitialize == true)
        schedulerUpdateCount = schedulerUpdateCount + 1
        return { policyConfig = { enabled = true } },
            "scheduled"
    end,
}

package.loaded["TGSRR/Helicopter/BasicSchedule"] = {
    id = "test",
    isEnabledInSandbox = function() return true end,
    chooseNext = function() return nil, "exhausted" end,
}

local Runtime = require "TGSRR/Helicopter/Runtime"
assert(type(gameStartHandler) == "function")
assert(type(dailyHandler) == "function")

local ok, status = Runtime.update()
assert(ok == true)
assert(status == "scheduled")
assert(schedulerUpdateCount == 1)
assert(helicopterValue == 1)
assert(SandboxVars.Helicopter == 1)

package.loaded["TGSRR/Helicopter/BasicSchedule"].isEnabledInSandbox =
    function() return false end
local disabled = Runtime.update()
assert(disabled == false)
assert(schedulerUpdateCount == 1)

print("helicopter runtime test passed")
