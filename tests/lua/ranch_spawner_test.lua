package.loaded["Definitions/animal/RanchZoneDefinitions"] = true

local rolls = {}
function ZombRand(minimum, maximum)
    local value = table.remove(rolls, 1)
    assert(value ~= nil, "unexpected random roll")
    if maximum == nil then
        assert(value >= 0 and value < minimum)
    else
        assert(value >= minimum and value < maximum)
    end
    return value
end

function ZombRandFloat(minimum, maximum)
    assert(minimum < maximum)
    return minimum
end

local Spawner = require "TGSRR/Animals/RanchSpawner"

local definitions = {
    chicken = {
        type = "chicken",
        chance = 20,
        femaleType = "hen",
        maleType = "cockerel",
    },
    cow = {
        type = "cow",
        chance = 10,
        femaleType = "cow",
        maleType = "bull",
    },
    mixed = {
        type = "mixed",
        possibleDef = { "chicken", "cow" },
    },
}

rolls = { 0 }
assert(Spawner.chooseDefinition("mixed", definitions) == definitions.chicken)

rolls = { 29 }
assert(Spawner.chooseDefinition("mixed", definitions) == definitions.cow)

assert(Spawner.ranchSpawnChance(1) == 0)
assert(Spawner.ranchSpawnChance(2) == 7)
assert(Spawner.ranchSpawnChance(3) == 6)
assert(Spawner.ranchSpawnChance(4) == 20)
assert(Spawner.ranchSpawnChance(5) == 55)
assert(Spawner.ranchSpawnChance(6) == 85)
assert(Spawner.ranchSpawnChance(7) == 120)

rolls = { 5 }
assert(Spawner.shouldPopulate(3) == true)
rolls = { 6 }
assert(Spawner.shouldPopulate(3) == false)

local mortalityCalls = {}
Spawner.setMortalityPolicy(function(sex, worldAgeDays, definition)
    mortalityCalls[#mortalityCalls + 1] = {
        sex = sex,
        worldAgeDays = worldAgeDays,
        definition = definition,
    }
    return false
end)

assert(#mortalityCalls == 0)

local breed = {}
local animalDefinition = {
    getBreedByName = function(_, name)
        assert(name == "testbreed")
        return breed
    end,
}
AnimalDefinitions = {
    getDef = function(animalType)
        assert(animalType == "hen" or animalType == "cockerel")
        return animalDefinition
    end,
}

local baby = {
    setWild = function(_, wild) assert(wild == false) end,
    randomizeAge = function(self) self.ageRandomized = true end,
    setHealth = function(self, health) self.health = health end,
}
local createdAnimals = {}
IsoAnimal = {
    new = function(_, x, y, z, animalType, selectedBreed)
        assert(selectedBreed == breed)
        local data = {
            canHaveBaby = function() return animalType == "hen" end,
            getMaxMilk = function() return 10 end,
            setMilkQuantity = function(self, quantity) self.milk = quantity end,
        }
        local animal = {
            animalType = animalType,
            x = x,
            y = y,
            z = z,
            data = data,
            setWild = function(self, wild) self.wild = wild end,
            addToWorld = function(self) self.added = true end,
            randomizeAge = function(self) self.ageRandomized = true end,
            getData = function() return data end,
            addBaby = function() return baby end,
            canBeMilked = function() return animalType == "hen" end,
            setHealth = function(self, health) self.health = health end,
        }
        createdAnimals[#createdAnimals + 1] = animal
        return animal
    end,
}

function getCell() return {} end
function getGameTime()
    return {
        getWorldAgeDaysSinceBegin = function() return 300 end,
    }
end

local square = {
    getX = function() return 11 end,
    getY = function() return 21 end,
}
local ranchZone = {
    getX = function() return 10 end,
    getY = function() return 20 end,
    getZ = function() return 0 end,
    getWidth = function() return 5 end,
    getHeight = function() return 5 end,
    getRandomFreeSquareInZone = function() return square end,
}

RanchZoneDefinitions = {
    type = {
        test = {
            type = "test",
            chance = 1,
            femaleType = "hen",
            maleType = "cockerel",
            minFemaleNb = 1,
            maxFemaleNb = 1,
            minMaleNb = 1,
            maxMaleNb = 1,
            maleChance = 100,
            chanceForBaby = 100,
            forcedBreed = "testbreed",
        },
    },
}

rolls = {
    0, -- Keep the male.
    0, -- Add a baby.
    12, -- Male x.
    22, -- Male y.
}
local populated, populateError = Spawner.populate(ranchZone, "test")
assert(populated, populateError)
assert(populated.females == 1)
assert(populated.males == 1)
assert(populated.babies == 1)
assert(#createdAnimals == 2)
assert(createdAnimals[1].animalType == "hen")
assert(createdAnimals[1].x == 11 and createdAnimals[1].y == 21)
assert(createdAnimals[1].wild == false)
assert(createdAnimals[1].added == true)
assert(createdAnimals[1].ageRandomized == true)
assert(createdAnimals[1].data.milk == 5.0)
assert(createdAnimals[1].health == nil)
assert(createdAnimals[2].animalType == "cockerel")
assert(createdAnimals[2].x == 12 and createdAnimals[2].y == 22)
assert(createdAnimals[2].health == nil)
assert(baby.ageRandomized == true)
assert(baby.health == nil)
assert(#mortalityCalls == 2)
assert(mortalityCalls[1].sex == "female")
assert(mortalityCalls[1].worldAgeDays == 300)
assert(mortalityCalls[2].sex == "male")

print("ranch spawner test passed")
