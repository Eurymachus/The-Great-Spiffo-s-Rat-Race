local player = {}

isServer = function() return false end
isDebugEnabled = function() return false end
CharacterStat = { THIRST = "thirst" }
Events = {
    OnPlayerUpdate = {
        Add = function(callback)
            Events.OnPlayerUpdate.callback = callback
        end,
    },
}

ISPetAnimal = {
    complete = function() return true end,
}
ISFixGenerator = {
    complete = function(action)
        action.generator.value =
            math.min(100, action.generator.value + 7)
        return true
    end,
}
ISEatFoodAction = {
    complete = function() return true end,
    eat = function() return true end,
}
ISDrinkFluidAction = {
    updateEat = function(action)
        action.fluidContainer.value =
            action.fluidContainer.value - 0.25
    end,
}
ISDrinkFromBottle = {
    drink = function() return true end,
}
ISTakeWaterAction = {
    transferFluid = function() return true end,
}

package.preload["TimedActions/Animals/ISPetAnimal"] =
    function() return true end
package.preload["TimedActions/ISFixGenerator"] =
    function() return true end
package.preload["TimedActions/ISEatFoodAction"] =
    function() return true end
package.preload["TimedActions/ISDrinkFluidAction"] =
    function() return true end
package.preload["TimedActions/ISDrinkFromBottle"] =
    function() return true end
package.preload["TimedActions/ISTakeWaterAction"] =
    function() return true end
package.loaded["TGSRR/Run/Recorder"] = {
    isActive = function() return true end,
    deactivate = function() end,
}
package.loaded["TGSRR/Run/TrackingHealth"] = {
    stop = function() error("tracking should not stop") end,
}

local run = {
    animalsPetted = {},
    animalsPettedTotal = 0,
    fluidConsumed = {},
    fluidConsumedTotal = 0,
    caloriesConsumed = 0,
    generatorRepairs = 0,
    generatorConditionRestored = 0,
}

local AnimalPetTracker = require "TGSRR/Run/AnimalPetTracker"
AnimalPetTracker.initialize(run, player)
ISPetAnimal.complete({
    character = player,
    animal = {
        getAnimalType = function() return "rabbitkit" end,
    },
})
assert(run.animalsPettedTotal == 1)
assert(run.animalsPetted.rabbitkit == 1)

local GeneratorRepairTracker =
    require "TGSRR/Run/GeneratorRepairTracker"
GeneratorRepairTracker.initialize(run, player)
local generator = {
    value = 96,
    getCondition = function(self) return self.value end,
}
ISFixGenerator.complete({
    character = player,
    generator = generator,
})
assert(run.generatorRepairs == 1)
assert(run.generatorConditionRestored == 4)

local fluid = {
    value = 1,
    calories = 120,
    getAmount = function(self) return self.value end,
    isMixture = function() return false end,
    getPrimaryFluid = function()
        return {
            getFluidTypeString = function() return "Coffee" end,
        }
    end,
    getProperties = function(self)
        return {
            getCalories = function() return self.calories end,
        }
    end,
}
local stats = { thirst = 0.2 }
player.getStats = function()
    return {
        get = function() return stats.thirst end,
    }
end
player.getInventory = function()
    return { getItems = function() return {} end }
end
player.getWaterSource = function()
    return {
        getFluidContainer = function() return fluid end,
    }
end

local ConsumptionTracker = require "TGSRR/Run/ConsumptionTracker"
ConsumptionTracker.initialize(run, player)

stats.thirst = 0.05
fluid.value = 0.8
ConsumptionTracker.sampleAutoDrink(player)
assert(math.abs(run.fluidConsumed.Coffee - 0.2) < 0.000001)
assert(math.abs(run.caloriesConsumed - 24) < 0.000001)

ISDrinkFluidAction.updateEat({
    character = player,
    fluidContainer = fluid,
}, 1)
assert(math.abs(run.fluidConsumed.Coffee - 0.45) < 0.000001)
assert(math.abs(run.caloriesConsumed - 61.5) < 0.000001)
ConsumptionTracker.sampleAutoDrink(player)
assert(math.abs(run.fluidConsumed.Coffee - 0.45) < 0.000001)

local food = {
    getBaseHunger = function() return -0.5 end,
    getHungChange = function() return -0.5 end,
    getThirstChange = function() return 0 end,
    getCalories = function() return 500 end,
    isBurnt = function() return true end,
}
ISEatFoodAction.complete({
    character = player,
    item = food,
    percentage = 0.5,
})
assert(math.abs(run.caloriesConsumed - 111.5) < 0.000001)

local AnimalPetSnapshot = require "TGSRR/Run/AnimalPetSnapshot"
local FluidConsumedSnapshot =
    require "TGSRR/Run/FluidConsumedSnapshot"
assert(AnimalPetSnapshot.list(run.animalsPetted)[1].pets == 1)
assert(math.abs(
    FluidConsumedSnapshot.list(run.fluidConsumed)[1].liters - 0.45)
    < 0.000001)

print("cumulative activity tracker test passed")
