local HelicopterScheduler = require "TGSRR/Core/HelicopterScheduler"
local BasicSchedule = require "TGSRR/Helicopter/BasicSchedule"
local ChallengeContext = require "TGSRR/Challenge/Context"

local Runtime = {}

local OPTIONS = {
    modDataKey = "TGSRR_HelicopterScheduler",
    policy = BasicSchedule,
    replaceScheduleOnInitialize = true,
}

local function claimVanillaScheduler()
    local sandboxOptions = getSandboxOptions()
    local helicopterOption = sandboxOptions
        and sandboxOptions:getOptionByName("Helicopter") or nil
    if helicopterOption then helicopterOption:setValue(1) end
    if SandboxVars then SandboxVars.Helicopter = 1 end
end

function Runtime.update()
    if not ChallengeContext.isActive() then return false, "inactive" end
    if not BasicSchedule.isEnabledInSandbox() then
        return false
    end

    claimVanillaScheduler()

    local state, status = HelicopterScheduler.update(OPTIONS)
    if not state then
        print("[TGSRR] Helicopter scheduler failed: " .. tostring(status))
        return false
    end
    return true, status
end

Runtime.claimVanillaScheduler = claimVanillaScheduler

Events.OnGameStart.Add(Runtime.update)
Events.EveryDays.Add(Runtime.update)

return Runtime
