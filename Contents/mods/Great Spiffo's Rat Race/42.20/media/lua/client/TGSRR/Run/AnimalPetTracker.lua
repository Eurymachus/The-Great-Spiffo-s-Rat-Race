require "TimedActions/Animals/ISPetAnimal"

local AnimalPetTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function animalType(animal)
    if not animal or not animal.getAnimalType then return nil end
    local ok, value = pcall(function()
        return animal:getAnimalType()
    end)
    if not ok or value == nil or tostring(value) == "" then return nil end
    return tostring(value)
end

local function record(character, value)
    if not activeRun or character ~= activePlayer or not value then
        return false
    end
    if isServer and isServer() then return false end
    activeRun.animalsPetted[value] =
        math.max(0, math.floor(tonumber(
            activeRun.animalsPetted[value]) or 0)) + 1
    activeRun.animalsPettedTotal =
        math.max(0, math.floor(tonumber(
            activeRun.animalsPettedTotal) or 0)) + 1
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Animals] Petted " .. value)
    end
    return true
end

local function install()
    if installed then return end
    installed = true
    local originalComplete = ISPetAnimal.complete
    ISPetAnimal.complete = function(action)
        local value = animalType(action and action.animal)
        local result = originalComplete(action)
        if result == true then
            record(action.character, value)
        end
        return result
    end
end

function AnimalPetTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return AnimalPetTracker
