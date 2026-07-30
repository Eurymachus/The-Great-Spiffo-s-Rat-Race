require "TimedActions/ISFixGenerator"

local GeneratorRepairTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function condition(generator)
    if not generator or not generator.getCondition then return nil end
    local ok, value = pcall(function()
        return generator:getCondition()
    end)
    if not ok then return nil end
    return tonumber(value)
end

local function record(character, restored)
    restored = math.max(0, tonumber(restored) or 0)
    if not activeRun or character ~= activePlayer or restored <= 0 then
        return false
    end
    if isServer and isServer() then return false end
    activeRun.generatorRepairs =
        math.max(0, math.floor(tonumber(
            activeRun.generatorRepairs) or 0)) + 1
    activeRun.generatorConditionRestored =
        math.max(0, tonumber(
            activeRun.generatorConditionRestored) or 0) + restored
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Generator] Repaired +" .. tostring(restored)
            .. " condition")
    end
    return true
end

local function install()
    if installed then return end
    installed = true
    local originalComplete = ISFixGenerator.complete
    ISFixGenerator.complete = function(action)
        local before = condition(action and action.generator)
        local result = originalComplete(action)
        local after = condition(action and action.generator)
        if result == true and before and after and after > before then
            record(action.character, after - before)
        end
        return result
    end
end

function GeneratorRepairTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return GeneratorRepairTracker
