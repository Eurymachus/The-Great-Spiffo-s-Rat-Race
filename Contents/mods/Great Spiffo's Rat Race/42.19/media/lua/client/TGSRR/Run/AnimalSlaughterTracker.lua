require "TimedActions/Animals/ISKillAnimal"
require "TimedActions/Animals/ISKillAnimalInInventory"

local AnimalSlaughterTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function animalType(animal)
    if not animal or not animal.getAnimalType then return nil end
    local ok, value = pcall(function() return animal:getAnimalType() end)
    if not ok or value == nil or tostring(value) == "" then return nil end
    return tostring(value)
end

local function record(character, value)
    if not activeRun or character ~= activePlayer or not value then
        return false
    end
    if isServer and isServer() then return false end

    activeRun.animalsSlaughtered[value] =
        math.max(0, math.floor(
            tonumber(activeRun.animalsSlaughtered[value]) or 0)) + 1
    activeRun.animalsSlaughteredTotal =
        math.max(0, math.floor(
            tonumber(activeRun.animalsSlaughteredTotal) or 0)) + 1

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Animals] Slaughtered " .. value)
    end
    return true
end

local function install()
    if installed then return end
    installed = true

    local originalWorldComplete = ISKillAnimal.complete
    ISKillAnimal.complete = function(action)
        local value = animalType(action and action.animal)
        local result = originalWorldComplete(action)
        if result == true then record(action.character, value) end
        return result
    end

    local originalInventoryComplete = ISKillAnimalInInventory.complete
    ISKillAnimalInInventory.complete = function(action)
        local item = action and action.animalItem
        local animal = item and item.getAnimal and item:getAnimal() or nil
        local value = animalType(animal)
        local result = originalInventoryComplete(action)
        if result == true then record(action.character, value) end
        return result
    end
end

function AnimalSlaughterTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return AnimalSlaughterTracker
