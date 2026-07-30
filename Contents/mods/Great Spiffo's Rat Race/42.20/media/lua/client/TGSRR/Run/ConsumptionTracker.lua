require "TimedActions/ISEatFoodAction"
require "TimedActions/ISDrinkFluidAction"
require "TimedActions/ISDrinkFromBottle"
require "TimedActions/ISTakeWaterAction"

local Recorder = require "TGSRR/Run/Recorder"
local TrackingHealth = require "TGSRR/Run/TrackingHealth"

local ConsumptionTracker = {}

local MIXED_FLUID_ID = "__MIXED__"
local activeRun = nil
local activePlayer = nil
local installed = false
local autoState = nil

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

local function amount(container)
    if not container or not container.getAmount then return nil end
    local ok, value = pcall(function() return container:getAmount() end)
    return ok and tonumber(value) or nil
end

local function propertiesCalories(container)
    if not container or not container.getProperties then return 0 end
    local ok, value = pcall(function()
        local properties = container:getProperties()
        return properties and properties:getCalories() or 0
    end)
    return ok and tonumber(value) or 0
end

local function fluidTypeId(container)
    if not container then return nil end
    local mixedOk, mixed = pcall(function()
        return container:isMixture()
    end)
    if mixedOk and mixed == true then return MIXED_FLUID_ID end
    local ok, value = pcall(function()
        local fluid = container:getPrimaryFluid()
        return fluid and fluid:getFluidTypeString() or nil
    end)
    if not ok or value == nil or tostring(value) == "" then return nil end
    return tostring(value)
end

local function thirst(player)
    if not player or not player.getStats or not CharacterStat then
        return nil
    end
    local ok, value = pcall(function()
        return player:getStats():get(CharacterStat.THIRST)
    end)
    return ok and tonumber(value) or nil
end

local function recordFluid(character, typeId, liters, route)
    liters = math.max(0, tonumber(liters) or 0)
    if not activeRun or character ~= activePlayer or not typeId
            or liters <= 0 then
        return false
    end
    if isServer and isServer() then return false end
    activeRun.fluidConsumed[typeId] =
        math.max(0, tonumber(activeRun.fluidConsumed[typeId]) or 0)
            + liters
    activeRun.fluidConsumedTotal =
        math.max(0, tonumber(activeRun.fluidConsumedTotal) or 0)
            + liters
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Consumption] Drank " .. tostring(liters)
            .. " L " .. typeId .. " (" .. tostring(route) .. ")")
    end
    return true
end

local function recordCalories(character, calories, route)
    calories = math.max(0, tonumber(calories) or 0)
    if not activeRun or character ~= activePlayer or calories <= 0 then
        return false
    end
    if isServer and isServer() then return false end
    activeRun.caloriesConsumed =
        math.max(0, tonumber(activeRun.caloriesConsumed) or 0)
            + calories
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Consumption] Consumed " .. tostring(calories)
            .. " kcal (" .. tostring(route) .. ")")
    end
    return true
end

local function observeManualContainer(container)
    if not autoState or autoState.container ~= container then return end
    autoState.amount = amount(container) or autoState.amount
    autoState.thirst = thirst(activePlayer) or autoState.thirst
    autoState.typeId = fluidTypeId(container) or autoState.typeId
    autoState.calories = propertiesCalories(container)
end

local function recordContainerDelta(character, container, beforeAmount,
        beforeType, beforeCalories, route)
    local afterAmount = amount(container)
    if beforeAmount and afterAmount and beforeAmount > afterAmount then
        local consumed = beforeAmount - afterAmount
        recordFluid(character, beforeType, consumed, route)
        if beforeAmount > 0 then
            recordCalories(character,
                math.max(0, tonumber(beforeCalories) or 0)
                    * consumed / beforeAmount,
                route)
        end
    end
    observeManualContainer(container)
end

local function effectiveFoodPercentage(food, requested)
    local percentage = clamp(tonumber(requested) or 0, 0, 1)
    local baseHunger = tonumber(food:getBaseHunger()) or 0
    local hungerChange = tonumber(food:getHungChange()) or 0
    if baseHunger ~= 0 and hungerChange ~= 0 then
        percentage = clamp(baseHunger * percentage / hungerChange, 0, 1)
    end
    if hungerChange < 0 and hungerChange * (1 - percentage) > -0.01 then
        percentage = 1
    end
    local thirstChange = tonumber(food:getThirstChange()) or 0
    if hungerChange == 0 and thirstChange < 0
            and thirstChange * (1 - percentage) > -0.01 then
        percentage = 1
    end
    return percentage
end

local function foodCalories(food, requested)
    if not food then return 0 end
    local ok, value = pcall(function()
        local calories = math.max(0, tonumber(food:getCalories()) or 0)
        local percentage = effectiveFoodPercentage(food, requested)
        if food:isBurnt() then calories = calories / 5 end
        return calories * percentage
    end)
    return ok and value or 0
end

local function install()
    if installed then return end
    installed = true

    local originalEatComplete = ISEatFoodAction.complete
    ISEatFoodAction.complete = function(action)
        local calories = foodCalories(
            action and action.item, action and action.percentage)
        local result = originalEatComplete(action)
        if result == true then
            recordCalories(action.character, calories, "food")
        end
        return result
    end

    local originalEatPartial = ISEatFoodAction.eat
    ISEatFoodAction.eat = function(action, food, percentage)
        local appliedPercentage =
            (tonumber(action and action.percentage) or 0)
                * (tonumber(percentage) or 0)
        local calories = foodCalories(food, appliedPercentage)
        local result = originalEatPartial(action, food, percentage)
        recordCalories(action.character, calories, "food_partial")
        return result
    end

    local originalDrinkFluid = ISDrinkFluidAction.updateEat
    ISDrinkFluidAction.updateEat = function(action, delta)
        local container = action and action.fluidContainer
        local beforeAmount = amount(container)
        local beforeType = fluidTypeId(container)
        local beforeCalories = propertiesCalories(container)
        local result = originalDrinkFluid(action, delta)
        recordContainerDelta(action.character, container, beforeAmount,
            beforeType, beforeCalories, "container")
        return result
    end

    local originalDrinkBottle = ISDrinkFromBottle.drink
    ISDrinkFromBottle.drink = function(action, food, percentage)
        local container = food and food.getFluidContainer
            and food:getFluidContainer() or nil
        local beforeAmount = amount(container)
        local beforeType = fluidTypeId(container)
        local result = originalDrinkBottle(action, food, percentage)
        recordContainerDelta(action.character, container, beforeAmount,
            beforeType, 0, "bottle")
        return result
    end

    local originalTakeWater = ISTakeWaterAction.transferFluid
    ISTakeWaterAction.transferFluid = function(action, requested)
        local directDrink = action and action.item == nil
        local object = action and action.waterObject
        local beforeAmount = directDrink and object
            and tonumber(object:getFluidAmount()) or nil
        local container = object and object.getFluidContainer
            and object:getFluidContainer() or nil
        local beforeType = fluidTypeId(container)
        if not beforeType and object and object.isTaintedWater
                and object:isTaintedWater() then
            beforeType = "TaintedWater"
        end
        beforeType = beforeType or "Water"
        local result = originalTakeWater(action, requested)
        local afterAmount = directDrink and object
            and tonumber(object:getFluidAmount()) or nil
        if beforeAmount and afterAmount and beforeAmount > afterAmount then
            recordFluid(action.character, beforeType,
                beforeAmount - afterAmount, "world_source")
        end
        return result
    end
end

local function selectedWaterSource(player)
    if not player or not player.getWaterSource
            or not player.getInventory then
        return nil
    end
    local ok, item = pcall(function()
        return player:getWaterSource(player:getInventory():getItems())
    end)
    if not ok or not item or not item.getFluidContainer then return nil end
    local container = item:getFluidContainer()
    if not container then return nil end
    return container
end

function ConsumptionTracker.sampleAutoDrink(player)
    player = player or activePlayer
    if not activeRun or player ~= activePlayer
            or not Recorder.isActive() then
        autoState = nil
        return false
    end
    local currentThirst = thirst(player)
    if autoState and autoState.container then
        local currentAmount = amount(autoState.container)
        if currentAmount and autoState.amount
                and autoState.amount > currentAmount
                and currentThirst and autoState.thirst
                and currentThirst < autoState.thirst then
            local consumed = autoState.amount - currentAmount
            recordFluid(player, autoState.typeId or "Water",
                consumed, "auto_drink")
            if autoState.amount > 0 then
                recordCalories(player,
                    math.max(0, tonumber(autoState.calories) or 0)
                        * consumed / autoState.amount,
                    "auto_drink")
            end
        end
    end
    local now = milliseconds()
    local container = autoState and autoState.container or nil
    local refresh = not autoState
        or now - (tonumber(autoState.sourceRefreshMs) or 0) >= 1000
        or (amount(container) or 0) < 0.12
    if refresh then container = selectedWaterSource(player) end
    autoState = container and {
        container = container,
        amount = amount(container),
        thirst = currentThirst,
        typeId = fluidTypeId(container) or "Water",
        calories = propertiesCalories(container),
        sourceRefreshMs = refresh and now
            or autoState and autoState.sourceRefreshMs or now,
    } or nil
    return true
end

function ConsumptionTracker.onPlayerUpdate(player)
    if player ~= activePlayer then return end
    local ok, result = pcall(
        ConsumptionTracker.sampleAutoDrink, player)
    if ok then return result end
    local failure = "consumption_tracker_failed:"
        .. tostring(result or "unknown_error")
    if activeRun then activeRun.integrityStatus = failure end
    Recorder.deactivate()
    activeRun = nil
    activePlayer = nil
    autoState = nil
    TrackingHealth.stop(
        failure,
        "Food and fluid consumption tracking raised an unexpected error."
    )
    return false
end

function ConsumptionTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    autoState = nil
    install()
    ConsumptionTracker.sampleAutoDrink(player)
end

Events.OnPlayerUpdate.Add(ConsumptionTracker.onPlayerUpdate)

return ConsumptionTracker
