require "Definitions/animal/RanchZoneDefinitions"

local Spawner = {}
local RanchMortality = require "TGSRR/Animals/RanchMortality"

local defaultMortalityPolicy = function(sex, worldAgeDays)
    return RanchMortality.shouldSpawnDead(sex, worldAgeDays)
end
local mortalityPolicy = defaultMortalityPolicy

local function int(value, fallback)
    return math.floor(tonumber(value) or fallback or 0)
end

local function randomInclusive(minimum, maximum)
    minimum = int(minimum)
    maximum = int(maximum, minimum)
    if maximum <= minimum then return minimum end
    return ZombRand(minimum, maximum + 1)
end

local function weightedDefinition(definitions)
    local total = 0
    for i = 1, #definitions do
        total = total + math.max(0, int(definitions[i].chance))
    end
    if total <= 0 then return nil end

    local roll = ZombRand(total)
    local cursor = 0
    for i = 1, #definitions do
        local definition = definitions[i]
        if math.max(0, int(definition.chance)) + cursor >= roll then
            return definition
        end
        cursor = cursor + math.max(0, int(definition.chance))
    end
    return definitions[#definitions]
end

local function expandPossible(definition, allDefinitions)
    if type(definition.possibleDef) ~= "table" then return definition end

    local possible = {}
    for i = 1, #definition.possibleDef do
        local candidate = allDefinitions[definition.possibleDef[i]]
        if type(candidate) == "table" and candidate.chance ~= nil then
            possible[#possible + 1] = candidate
        end
    end
    return weightedDefinition(possible)
end

function Spawner.chooseDefinition(ranchName, allDefinitions)
    allDefinitions = allDefinitions
        or (RanchZoneDefinitions and RanchZoneDefinitions.type)
    if type(allDefinitions) ~= "table" then return nil, "definitions_unavailable" end

    if ranchName and ranchName ~= "" then
        local definition = allDefinitions[ranchName]
        if type(definition) ~= "table" then
            return nil, "definition_not_found:" .. tostring(ranchName)
        end
        definition = expandPossible(definition, allDefinitions)
        if not definition then return nil, "possible_definition_unavailable" end
        return definition
    end

    local possible = {}
    for _, definition in pairs(allDefinitions) do
        if type(definition) == "table" and definition.chance ~= nil then
            possible[#possible + 1] = definition
        end
    end
    local definition = weightedDefinition(possible)
    if not definition then return nil, "no_weighted_definition" end
    return definition
end

function Spawner.ranchSpawnChance(setting)
    setting = int(setting, 3)
    if setting == 1 then return 0 end
    if setting == 2 then return 7 end
    if setting == 4 then return 20 end
    if setting == 5 then return 55 end
    if setting == 6 then return 85 end
    if setting == 7 then return 120 end
    return 6
end

function Spawner.shouldPopulate(setting)
    return ZombRand(100) < Spawner.ranchSpawnChance(setting)
end

function Spawner.setMortalityPolicy(policy)
    mortalityPolicy = type(policy) == "function"
        and policy or defaultMortalityPolicy
end

local function randomBreed(animalDefinition, forcedBreed)
    if forcedBreed and forcedBreed ~= "" then
        local breed = animalDefinition:getBreedByName(forcedBreed)
        if breed then return breed end
    end
    local breeds = animalDefinition:getBreeds()
    if not breeds or breeds:size() <= 0 then return nil end
    return breeds:get(ZombRand(breeds:size()))
end

local function createAnimal(zone, animalType, breed, square)
    local x = square and square:getX()
        or ZombRand(zone:getX(), zone:getX() + zone:getWidth())
    local y = square and square:getY()
        or ZombRand(zone:getY(), zone:getY() + zone:getHeight())
    local animal = IsoAnimal.new(getCell(), x, y, zone:getZ(), animalType, breed)
    if not animal then return nil end
    animal:setWild(false)
    animal:addToWorld()
    animal:randomizeAge()
    return animal
end

local function spawnFemale(zone, definition, femaleDefinition, worldAgeDays)
    local square = zone:getRandomFreeSquareInZone()
    if not square then return nil, nil, "no_free_square" end

    local breed = randomBreed(femaleDefinition, definition.forcedBreed)
    local animal = createAnimal(
        zone, definition.femaleType, breed, square)
    if not animal then return nil, nil, "animal_creation_failed" end

    local baby = nil
    if animal:getData():canHaveBaby()
            and ZombRand(100) <= int(definition.chanceForBaby) then
        baby = animal:addBaby()
        if baby then
            baby:setWild(false)
            baby:randomizeAge()
        end
        if baby and animal:canBeMilked() then
            local data = animal:getData()
            data:setMilkQuantity(
                ZombRandFloat(5.0, data:getMaxMilk()))
        end
    end

    if mortalityPolicy("female", worldAgeDays, definition, animal) then
        animal:setHealth(0.0)
        if baby then baby:setHealth(0.0) end
    end
    return animal, baby
end

local function spawnMale(zone, definition, maleDefinition, worldAgeDays)
    local breed = randomBreed(maleDefinition, definition.forcedBreed)
    local animal = createAnimal(zone, definition.maleType, breed, nil)
    if animal and mortalityPolicy(
            "male", worldAgeDays, definition, animal) then
        animal:setHealth(0.0)
    end
    return animal
end

function Spawner.populate(zone, ranchName)
    local definition, definitionError =
        Spawner.chooseDefinition(ranchName)
    if not definition then return nil, definitionError end

    local femaleDefinition = AnimalDefinitions.getDef(definition.femaleType)
    local maleDefinition = AnimalDefinitions.getDef(definition.maleType)
    if not femaleDefinition then
        return nil, "female_definition_not_found:" .. tostring(definition.femaleType)
    end
    if not maleDefinition then
        return nil, "male_definition_not_found:" .. tostring(definition.maleType)
    end

    local worldAgeDays = getGameTime():getWorldAgeDaysSinceBegin()
    local femaleCount = randomInclusive(
        definition.minFemaleNb, definition.maxFemaleNb)
    local maleCount = randomInclusive(
        definition.minMaleNb, definition.maxMaleNb)
    if ZombRand(100) > int(definition.maleChance) then maleCount = 0 end

    local result = {
        definition = definition,
        females = 0,
        males = 0,
        babies = 0,
        errors = {},
    }

    for _ = 1, femaleCount do
        local animal, baby, spawnError =
            spawnFemale(zone, definition, femaleDefinition, worldAgeDays)
        if animal then result.females = result.females + 1 end
        if baby then result.babies = result.babies + 1 end
        if spawnError then result.errors[#result.errors + 1] = spawnError end
    end

    for _ = 1, maleCount do
        local animal = spawnMale(
            zone, definition, maleDefinition, worldAgeDays)
        if animal then result.males = result.males + 1 end
    end

    return result
end

return Spawner
