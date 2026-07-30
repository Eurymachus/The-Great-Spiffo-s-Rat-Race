require "Traps/TimedActions/ISCheckTrapAction"

local AnimalTrapTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function resolvedTrap(action)
    local trap = action and action.trap or nil
    if not trap then return nil end
    if STrapSystem and STrapSystem.instance
            and STrapSystem.instance.getLuaObjectAt then
        return STrapSystem.instance:getLuaObjectAt(
            trap.x, trap.y, trap.z) or trap
    end
    return trap
end

local function evidence(trap)
    local animal = trap and trap.animal or nil
    local animalType = animal and animal.type or nil
    local trapId = trap and trap.trapType or nil
    if not animalType or tostring(animalType) == ""
            or not trapId or tostring(trapId) == "" then
        return nil
    end
    return tostring(animalType), tostring(trapId)
end

local function record(character, animalType, trapId)
    if not activeRun or character ~= activePlayer
            or not animalType or not trapId then
        return false
    end
    if isServer and isServer() then return false end

    local animals = activeRun.animalsTrapped
    animals[animalType] = type(animals[animalType]) == "table"
        and animals[animalType] or {}
    animals[animalType][trapId] =
        math.max(0, math.floor(
            tonumber(animals[animalType][trapId]) or 0)) + 1
    activeRun.animalsTrappedTotal =
        math.max(0, math.floor(
            tonumber(activeRun.animalsTrappedTotal) or 0)) + 1

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Traps] Claimed " .. animalType
            .. " from " .. trapId)
    end
    return true
end

local function install()
    if installed then return end
    installed = true
    local originalComplete = ISCheckTrapAction.complete
    ISCheckTrapAction.complete = function(action)
        local animalType, trapId = evidence(resolvedTrap(action))
        local result = originalComplete(action)
        if result == true then
            record(action.character, animalType, trapId)
        end
        return result
    end
end

function AnimalTrapTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return AnimalTrapTracker
