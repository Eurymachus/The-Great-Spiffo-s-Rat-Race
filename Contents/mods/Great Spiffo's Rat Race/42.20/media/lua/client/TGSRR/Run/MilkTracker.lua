require "TimedActions/Animals/ISMilkAnimal"

local MilkTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function milkQuantity(animal)
    if not animal or not animal.getData then return nil end
    local ok, value = pcall(function()
        return animal:getData():getMilkQuantity()
    end)
    if not ok then return nil end
    return tonumber(value)
end

local function milkType(animal)
    if not animal or not animal.getMilkType then return nil end
    local ok, value = pcall(function() return animal:getMilkType() end)
    if not ok or value == nil or tostring(value) == "" then return nil end
    return tostring(value)
end

local function record(character, value, amount)
    amount = tonumber(amount) or 0
    if not activeRun or character ~= activePlayer or not value
            or amount <= 0 then
        return false
    end
    if isServer and isServer() then return false end

    activeRun.milkCollected[value] =
        math.max(0, tonumber(activeRun.milkCollected[value]) or 0) + amount
    activeRun.milkCollectedTotal =
        math.max(0, tonumber(activeRun.milkCollectedTotal) or 0) + amount

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Animals] Collected " .. tostring(amount)
            .. " " .. value)
    end
    return true
end

local function install()
    if installed then return end
    installed = true

    local originalMilk = ISMilkAnimal.milk
    ISMilkAnimal.milk = function(action)
        local animal = action and action.animal
        local before = milkQuantity(animal)
        local value = milkType(animal)
        local result = originalMilk(action)
        local after = milkQuantity(animal)
        if before and after and before > after then
            record(action.character, value, before - after)
        end
        return result
    end
end

function MilkTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return MilkTracker
