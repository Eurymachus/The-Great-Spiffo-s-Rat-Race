local AnimalBirthTracker = {}

local MOD_DATA_ID = "TGSRR_RunAnimalId"
local SCAN_INTERVAL_SECONDS = 5

local activeRun = nil
local activePlayer = nil
local nextScanMilliseconds = 0

local function milliseconds()
    if getTimestampMs then return tonumber(getTimestampMs()) or 0 end
    return os.clock() * 1000
end

local function javaValues(values, result, seen)
    if not values then return end
    -- IsoCell:getAnimals() is declared as java.util.List and currently returns
    -- a LinkedList. Kahlua can receive it but cannot expose size/get through
    -- that interface-backed value. Copy every incoming Collection into the
    -- concrete ArrayList class that PZ exposes to Lua.
    local accessible = ArrayList.new(values)
    for index = 0, accessible:size() - 1 do
        local value = accessible:get(index)
        if value and not seen[value] then
            seen[value] = true
            result[#result + 1] = value
        end
    end
end

local function loadedAnimals()
    local result = {}
    local seen = setmetatable({}, { __mode = "k" })
    local cell = getCell and getCell() or nil
    if not cell then return result end
    javaValues(cell:getAnimals(), result, seen)
    local vehicles = cell:getVehicles()
    if vehicles then
        for index = 0, vehicles:size() - 1 do
            javaValues(vehicles:get(index):getAnimals(), result, seen)
        end
    end
    local zones = DesignationZoneAnimal
        and DesignationZoneAnimal.getAllZones
        and DesignationZoneAnimal.getAllZones() or nil
    if zones then
        for zoneIndex = 0, zones:size() - 1 do
            local hutches = zones:get(zoneIndex):getHutchsConnected()
            for hutchIndex = 0, hutches:size() - 1 do
                javaValues(
                    hutches:get(hutchIndex):getAnimalInside():values(),
                    result,
                    seen)
            end
        end
    end
    return result
end

local function nonWild(animal)
    if not animal or not animal.isWild then return false end
    local ok, value = pcall(function() return animal:isWild() end)
    return ok and value == false
end

local function pzId(animal)
    local ok, value = pcall(function() return animal:getAnimalID() end)
    return ok and math.floor(tonumber(value) or 0) or 0
end

local function animalType(animal)
    local ok, value = pcall(function() return animal:getAnimalType() end)
    return ok and value and tostring(value) or ""
end

local function breed(animal)
    local ok, value = pcall(function()
        return animal:getData():getBreed():getName()
    end)
    return ok and value and tostring(value) or ""
end

local function token(animal)
    local data = animal and animal.getModData and animal:getModData() or nil
    local value = data and data[MOD_DATA_ID] or nil
    if value == nil or tostring(value) == "" then return nil end
    return tostring(value)
end

local function motherToken(animal)
    local mother = animal:getMother()
    local value = mother and token(mother) or nil
    if value then return value end
    local id = math.floor(tonumber(animal.motherId) or 0)
    if id <= 0 then
        id = math.floor(tonumber(animal.attachBackToMother) or 0)
    end
    return id > 0
        and activeRun.animalIdentityByPzId[tostring(id)] or nil
end

local function register(animal, value)
    local id = pzId(animal)
    activeRun.animalIdentities[value] = {
        pzAnimalId = id,
        animalType = animalType(animal),
        breed = breed(animal),
    }
    if id > 0 then activeRun.animalIdentityByPzId[tostring(id)] = value end
end

local function assign(animal, value)
    if not value then
        activeRun.animalIdentitySequence =
            math.max(0, math.floor(tonumber(
                activeRun.animalIdentitySequence) or 0)) + 1
        value = tostring(activeRun.runId) .. "-animal-"
            .. tostring(activeRun.animalIdentitySequence)
    end
    animal:getModData()[MOD_DATA_ID] = value
    register(animal, value)
    return value
end

local function restoreAdultIdentity(animal)
    local value = token(animal)
    if value then
        register(animal, value)
        return value
    end
    local id = pzId(animal)
    value = id > 0
        and activeRun.animalIdentityByPzId[tostring(id)] or nil
    return assign(animal, value)
end

local function recordBirth(animal)
    local value = animalType(animal)
    if value == "" then return false end
    activeRun.animalBirths[value] =
        math.max(0, math.floor(
            tonumber(activeRun.animalBirths[value]) or 0)) + 1
    activeRun.animalBirthsTotal =
        math.max(0, math.floor(
            tonumber(activeRun.animalBirthsTotal) or 0)) + 1
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Animals] Domestic birth: " .. value)
    end
    return true
end

local function reconcile(baseline)
    if not activeRun or not activePlayer then return end
    local animals = loadedAnimals()
    local knownBefore = {}

    for _, animal in ipairs(animals) do
        if nonWild(animal) then
            local value = token(animal)
            if value then
                knownBefore[value] = true
                register(animal, value)
            end
        end
    end

    for _, animal in ipairs(animals) do
        if nonWild(animal) and not animal:isBaby() then
            local value = restoreAdultIdentity(animal)
            if baseline then knownBefore[value] = true end
        end
    end

    for _, animal in ipairs(animals) do
        if nonWild(animal) and animal:isBaby() and not token(animal) then
            local motherId = motherToken(animal)
            if not baseline and motherId and knownBefore[motherId] then
                recordBirth(animal)
            end
            assign(animal)
        elseif nonWild(animal) and animal:isBaby() then
            register(animal, token(animal))
        end
    end

    activeRun.animalBirthTrackingInitialized = true
end

function AnimalBirthTracker.onPlayerUpdate(player)
    if not activeRun or player ~= activePlayer then return end
    local now = milliseconds()
    if now < nextScanMilliseconds then return end
    nextScanMilliseconds = now + SCAN_INTERVAL_SECONDS * 1000
    reconcile(false)
end

function AnimalBirthTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    nextScanMilliseconds = milliseconds()
        + SCAN_INTERVAL_SECONDS * 1000
    reconcile(run.animalBirthTrackingInitialized ~= true)
end

Events.OnPlayerUpdate.Add(AnimalBirthTracker.onPlayerUpdate)

return AnimalBirthTracker
