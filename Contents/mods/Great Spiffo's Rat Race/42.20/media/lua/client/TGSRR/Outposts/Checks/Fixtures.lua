local Outposts = require "TGSRR/Outposts/Definitions"
local Resolver = require "TGSRR/Outposts/WorldResolver"
local Store = require "TGSRR/Outposts/ProgressStore"
local Notifications = require "TGSRR/Challenge/Notifications"
local ChallengeEvents = require "TGSRR/Core/Events"

local Fixtures = {}
local BoxedFood = require "TGSRR/Outposts/Checks/BoxedFood"
local GeneratorCoverage = require "TGSRR/Outposts/Checks/GeneratorCoverage"
local roomsByOutpost = {}
local outpostByRoom = {}
local generatorObjects = {}
local containersByOutpost = {}
local sinksByOutpost = {}
local nextGeneratorReconcileAt = 0
local indexBuilt = false
local FOOD_REQUIRED_CALORIES = 5000
local NEVER_SPOILS = 1000000000

local function buildIndex()
    if indexBuilt then return end
    roomsByOutpost = {}
    outpostByRoom = {}
    for _, outpost in ipairs(Outposts.getAll()) do
        local rooms = Resolver.resolveRooms(outpost)
        local registered = {}
        for _, room in ipairs(rooms) do
            registered[room.id] = true
            outpostByRoom[room.id] = outpost
        end
        roomsByOutpost[outpost.id] = registered
    end
    indexBuilt = true
end

local function isGoodBed(object)
    return object and object:getProperty("BedType") == "goodBed"
end

local function outpostForSquare(square)
    if not square then return nil end
    buildIndex()
    local room = square:getRoom()
    local roomDef = room and room:getRoomDef() or nil
    return roomDef and outpostByRoom[tostring(roomDef:getIDString())] or nil
end

local function fixtureKey(object)
    local square = object and object:getSquare() or nil
    if not square then return nil end
    local sprite = object:getSprite()
    local spriteName = sprite and sprite:getName() or object:getObjectName() or "<unknown>"
    return tostring(square:getX()) .. ":" .. tostring(square:getY()) .. ":"
        .. tostring(square:getZ()) .. ":" .. tostring(spriteName)
end

local function goodBedResult(outpost)
    local passed = Store.getFixtureCount(outpost.id, "good_bed") > 0
    return { available = true, passed = passed, current = passed and 1 or 0, required = 1 }
end

local function appendObjectContainers(target, object)
    if not object or not object.getContainerCount then return end
    for index = 0, object:getContainerCount() - 1 do
        local container = object:getContainerByIndex(index)
        if container then target[#target + 1] = { object = object, container = container } end
    end
end

local function isSink(object)
    local sprite = object and object:getSprite() or nil
    local properties = sprite and sprite:getProperties() or nil
    if not properties or not properties:has(IsoFlagType.waterPiped) then return false end
    local customName = properties:has("CustomName") and properties:get("CustomName") or ""
    return string.find(string.lower(customName), "sink", 1, true) ~= nil
end

local function appendSink(target, object)
    if isSink(object) then target[#target + 1] = object end
end

local function groundFloorRoomsFullyStreamed(outpost)
    for _, room in ipairs(Resolver.resolveRooms(outpost)) do
        if room.level == outpost.sealingLevel then
            local isoRoom = room.definition:getIsoRoom()
            local squares = isoRoom and isoRoom:getSquares() or nil
            if not squares or squares:size() < room.definition:getArea() then return false end
        end
    end
    return true
end

local function invalidateRoomCache(outpostId)
    containersByOutpost[outpostId] = nil
    sinksByOutpost[outpostId] = nil
end

local function buildContainerCache(outpost)
    if not groundFloorRoomsFullyStreamed(outpost) then
        invalidateRoomCache(outpost.id)
        return nil
    end
    local cache = {}
    local sinks = {}
    for _, room in ipairs(Resolver.resolveRooms(outpost)) do
        if room.level == outpost.sealingLevel then
            local isoRoom = room.definition:getIsoRoom()
            local squares = isoRoom and isoRoom:getSquares() or nil
            for squareIndex = 0, squares:size() - 1 do
                local square = squares:get(squareIndex)
                local objects = square and square:getObjects() or nil
                if objects then
                    for objectIndex = 0, objects:size() - 1 do
                        local object = objects:get(objectIndex)
                        appendObjectContainers(cache, object)
                        appendSink(sinks, object)
                    end
                end
            end
        end
    end
    containersByOutpost[outpost.id] = cache
    sinksByOutpost[outpost.id] = sinks
    return cache
end

local function roomCache(outpost)
    if not groundFloorRoomsFullyStreamed(outpost) then
        invalidateRoomCache(outpost.id)
        return nil
    end
    local cache = containersByOutpost[outpost.id]
    if cache then
        for _, entry in ipairs(cache) do
            if not entry.object:getSquare() then
                invalidateRoomCache(outpost.id)
                cache = nil
                break
            end
        end
    end
    local sinks = sinksByOutpost[outpost.id]
    if sinks then
        for _, sink in ipairs(sinks) do
            if not sink:getSquare() then
                invalidateRoomCache(outpost.id)
                cache = nil
                break
            end
        end
    end
    return cache or buildContainerCache(outpost)
end

local function caloriesInContainer(container, visited)
    if not container or visited[container] then return 0 end
    visited[container] = true
    local calories = 0
    local items = container:getItems()
    for index = 0, items:size() - 1 do
        local item = items:get(index)
        if instanceof(item, "Food") and item:getOffAgeMax() == NEVER_SPOILS then
            calories = calories + math.max(0, item:getCalories())
        else
            calories = calories + BoxedFood.calories(item, NEVER_SPOILS)
        end
        if instanceof(item, "InventoryContainer") then
            calories = calories + caloriesInContainer(item:getItemContainer(), visited)
        end
    end
    return calories
end

local function foodResult(outpost)
    local cache = roomCache(outpost)
    if not cache then
        return { available = false, passed = false, current = 0, required = FOOD_REQUIRED_CALORIES }
    end
    local calories = 0
    local visited = {}
    for _, entry in ipairs(cache) do
        if entry.object:getSquare() then
            calories = calories + caloriesInContainer(entry.container, visited)
        end
    end
    calories = math.floor(calories + 0.5)
    return {
        available = true,
        passed = calories >= FOOD_REQUIRED_CALORIES,
        current = calories,
        required = FOOD_REQUIRED_CALORIES,
    }
end

local function plumbedSinkResult(outpost)
    if not roomCache(outpost) then
        return { available = false, passed = false, current = 0, required = 1 }
    end
    local sinks = sinksByOutpost[outpost.id]
    local plumbed = false
    for _, sink in ipairs(sinks) do
        if sink:getSquare() and sink:getUsesExternalWaterSource() then
            plumbed = true
            if sink:FindExternalWaterSource() then
                return { available = true, passed = true, current = 1, required = 1, state = "connected" }
            end
        end
    end
    if #sinks == 0 then
        return { available = true, passed = false, current = 0, required = 1, state = "none" }
    end
    if plumbed then
        return { available = true, passed = false, current = 0, required = 1, state = "source_missing" }
    end
    return { available = true, passed = false, current = 0, required = 1, state = "not_plumbed" }
end

local function registerGenerator(object)
    if not object or not instanceof(object, "IsoGenerator") then return nil end
    local square = object:getSquare()
    if not square then return nil end
    for _, outpost in ipairs(Outposts.getAll()) do
        if GeneratorCoverage.covers(outpost, object) then
            local key = fixtureKey(object)
            if not key then return nil end
            Store.addFixture(outpost.id, "generator", key, {
                x = square:getX(), y = square:getY(), z = square:getZ(),
                sprite = object:getSprite() and object:getSprite():getName() or nil,
            })
            generatorObjects[key] = object
            return outpost
        end
    end
    return nil
end

-- IsoGenerator:addToWorld() registers loaded generators in this engine-maintained
-- list even when placement does not raise the Lua OnObjectAdded event.
local function reconcileGeneratorsFromCell()
    local now = getTimestampMs()
    if now < nextGeneratorReconcileAt then return end
    nextGeneratorReconcileAt = now + 1000

    local cell = getCell and getCell() or nil
    local objects = cell and cell.getProcessIsoObjects and cell:getProcessIsoObjects() or nil
    if not objects then return end
    generatorObjects = {}
    for index = 0, objects:size() - 1 do
        local object = objects:get(index)
        if instanceof(object, "IsoGenerator") then registerGenerator(object) end
    end
end

local function syncGoodBed(outpost)
    local changed, current, previous = Store.updateDeliverable(outpost.id, "good_bed", goodBedResult(outpost))
    if changed then
        Notifications.emit(outpost.id, "good_bed")
        ChallengeEvents.emit("outpost.deliverable.changed", {
            outpostId = outpost.id, deliverableId = "good_bed",
            previous = previous, current = current,
        })
        if previous and previous.passed ~= true and current and current.passed == true then
            ChallengeEvents.emit("outpost.deliverable.completed", {
                outpostId = outpost.id, deliverableId = "good_bed",
                previous = previous, current = current,
            })
        end
    end
end

local function findGeneratorAt(entry, key)
    local cached = generatorObjects[key]
    if cached and cached:getSquare() then return cached end
    local square = getCell():getGridSquare(entry.x, entry.y, entry.z)
    if not square then return nil, false end
    local objects = square:getObjects()
    for index = 0, objects:size() - 1 do
        local object = objects:get(index)
        if instanceof(object, "IsoGenerator") and fixtureKey(object) == key then
            generatorObjects[key] = object
            return object, true
        end
    end
    return nil, true
end

local function generatorResult(outpost)
    reconcileGeneratorsFromCell()
    local entries = Store.getFixtureEntries(outpost.id, "generator")
    local found = 0
    local unresolved = false
    local bestConnectedFuel = nil
    for key, entry in pairs(entries) do
        local generator, squareLoaded = findGeneratorAt(entry, key)
        if generator and GeneratorCoverage.covers(outpost, generator) then
            found = found + 1
            if generator:isConnected() then
                local fuel = generator:getFuelPercentage()
                if not bestConnectedFuel or fuel > bestConnectedFuel then bestConnectedFuel = fuel end
            end
        elseif not squareLoaded then
            unresolved = true
        end
    end
    if unresolved and found == 0 then
        return { available = false, passed = false, current = 0, required = 100 }
    end
    if found == 0 then
        return { available = true, passed = false, current = 0, required = 100, state = "none" }
    end
    if bestConnectedFuel == nil then
        return { available = true, passed = false, current = 0, required = 100, state = "not_connected" }
    end
    local fuel = math.max(0, math.min(100, bestConnectedFuel))
    return {
        available = true,
        passed = fuel >= 99.999,
        current = fuel,
        required = 100,
        state = "fuel",
        details = { fuelPercent = fuel },
    }
end

local function onObjectAdded(object)
    local square = object:getSquare()
    local outpost = outpostForSquare(square)
    if outpost and square:getZ() == outpost.sealingLevel and containersByOutpost[outpost.id] then
        appendObjectContainers(containersByOutpost[outpost.id], object)
        appendSink(sinksByOutpost[outpost.id], object)
    end
    if isGoodBed(object) then
        if not outpost or square:getZ() ~= outpost.sealingLevel then return end
        local key = fixtureKey(object)
        if key and Store.addFixture(outpost.id, "good_bed", key, {
            x = square:getX(), y = square:getY(), z = square:getZ(),
            sprite = object:getSprite() and object:getSprite():getName() or nil,
        }) then
            syncGoodBed(outpost)
        end
        return
    end
end

local function onObjectAboutToBeRemoved(object)
    local square = object:getSquare()
    local outpost = outpostForSquare(square)
    local cache = outpost and containersByOutpost[outpost.id] or nil
    if cache then
        for index = #cache, 1, -1 do
            if cache[index].object == object then table.remove(cache, index) end
        end
    end
    local sinks = outpost and sinksByOutpost[outpost.id] or nil
    if sinks then
        for index = #sinks, 1, -1 do
            if sinks[index] == object then table.remove(sinks, index) end
        end
    end
    if isGoodBed(object) then
        if not outpost or square:getZ() ~= outpost.sealingLevel then return end
        local key = fixtureKey(object)
        if key and Store.removeFixture(outpost.id, "good_bed", key) then syncGoodBed(outpost) end
        return
    end
end

function Fixtures.rebuildIndex()
    indexBuilt = false
    containersByOutpost = {}
    sinksByOutpost = {}
    buildIndex()
end

function Fixtures.getOutpostForRoom(roomId)
    buildIndex()
    return outpostByRoom[tostring(roomId)]
end

function Fixtures.getRoomsForOutpost(outpostId)
    buildIndex()
    return roomsByOutpost[outpostId]
end

function Fixtures.getSinksForOutpost(outpost)
    if not outpost or not roomCache(outpost) then return nil end
    return sinksByOutpost[outpost.id]
end

function Fixtures.inspectPlumbedSink(outpost)
    return plumbedSinkResult(outpost)
end

function Fixtures.getGeneratorsForOutpost(outpost)
    if not outpost then return {} end
    reconcileGeneratorsFromCell()
    local result = {}
    for key, entry in pairs(Store.getFixtureEntries(outpost.id, "generator")) do
        local generator = findGeneratorAt(entry, key)
        if generator and GeneratorCoverage.covers(outpost, generator) then
            result[#result + 1] = generator
        end
    end
    return result
end

function Fixtures.inspectGenerator(outpost)
    return generatorResult(outpost)
end

Outposts.addCheck("good_bed", goodBedResult, 60)
Outposts.addCheck("generator", generatorResult, 70)
Outposts.addCheck("food", foodResult, 80)
Outposts.addCheck("plumbed_sink", plumbedSinkResult, 90)
Events.OnObjectAdded.Add(onObjectAdded)
Events.OnObjectAboutToBeRemoved.Add(onObjectAboutToBeRemoved)
Events.OnGameStart.Add(Fixtures.rebuildIndex)

return Fixtures
