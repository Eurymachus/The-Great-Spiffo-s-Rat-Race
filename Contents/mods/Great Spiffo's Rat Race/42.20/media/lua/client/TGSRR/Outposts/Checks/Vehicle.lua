local Outposts = require "TGSRR/Outposts/Definitions"
local Inspector = require "TGSRR/Outposts/VehicleInspector"

local Check = {}

-- Match the practical B42.20 ignition requirements. Vanilla permits an engine
-- above 0% to start, but engines below 50% are subject to random running stalls,
-- so a Rat Race spare car requires 50% for reliable operation.
local REQUIREMENTS = {
    engineCondition = 50,
    engineQuality = 1,
    batteryCharge = 12.5,
}

local function hasAllTyresInstalled(facts)
    if not facts or #facts.tyres == 0 then return false end
    for _, tyre in ipairs(facts.tyres) do
        if tyre.installed ~= true then return false end
    end
    return true
end

local function inSupportArea(outpost, vehicle)
    local zone = outpost.coreZone
    local radius = outpost.supportRadius or 15
    local x, y = vehicle:getX(), vehicle:getY()
    local dx = math.max(zone.minX - x, 0, x - zone.maxX)
    local dy = math.max(zone.minY - y, 0, y - zone.maxY)
    return dx * dx + dy * dy <= radius * radius
end

local function supportAreaFullyLoaded(outpost)
    local cell = getCell and getCell() or nil
    if not cell then return false end
    local zone = outpost.coreZone
    local radius = outpost.supportRadius or 15
    local minX, minY = zone.minX - radius, zone.minY - radius
    local maxX, maxY = zone.maxX + radius, zone.maxY + radius
    -- One representative square per world chunk is sufficient to establish that
    -- every chunk capable of containing a qualifying vehicle is streamed.
    local firstChunkX, lastChunkX = math.floor(minX / 10), math.floor(maxX / 10)
    local firstChunkY, lastChunkY = math.floor(minY / 10), math.floor(maxY / 10)
    for chunkX = firstChunkX, lastChunkX do
        for chunkY = firstChunkY, lastChunkY do
            local chunkMinX, chunkMinY = chunkX * 10, chunkY * 10
            local chunkMaxX, chunkMaxY = chunkMinX + 9, chunkMinY + 9
            local dx = math.max(zone.minX - chunkMaxX, 0, chunkMinX - zone.maxX)
            local dy = math.max(zone.minY - chunkMaxY, 0, chunkMinY - zone.maxY)
            local x = math.max(chunkMinX, math.min(zone.minX, chunkMaxX))
            local y = math.max(chunkMinY, math.min(zone.minY, chunkMaxY))
            if dx * dx + dy * dy <= radius * radius
                    and not cell:getGridSquare(x, y, outpost.sealingLevel or 0) then
                return false
            end
        end
    end
    return true
end

local function evaluate(facts)
    local failures = {}
    local function requireFact(ok, id)
        if not ok then failures[#failures + 1] = id end
    end
    requireFact(facts.engine.installed and facts.engine.condition >= REQUIREMENTS.engineCondition,
        "engine_condition")
    requireFact(facts.engineQuality >= REQUIREMENTS.engineQuality, "engine_quality")
    requireFact(facts.fuel.installed and facts.fuel.currentRounded > 0, "fuel")
    if not facts.battery.installed then
        requireFact(false, "battery")
    else
        requireFact(facts.battery.charge >= REQUIREMENTS.batteryCharge, "battery_charge")
    end
    requireFact(facts.driverSeat.installed, "driver_seat")
    requireFact(hasAllTyresInstalled(facts), "tyres")
    return failures
end

local function isCar(vehicle)
    local name = vehicle and vehicle:getScriptName() or ""
    return name ~= "" and not string.find(name, "Trailer", 1, true)
        and not string.find(name, "Burnt", 1, true)
        and not string.find(name, "Smashed", 1, true)
end

local function vehicleResult(outpost)
    local cell = getCell and getCell() or nil
    local vehicles = cell and cell:getVehicles() or nil
    if not vehicles then return { available = false, passed = false, current = 0, required = 0 } end

    local bestFacts, bestFailures = nil, nil
    local candidates = 0
    -- IsoCell vehicles are a Java Set in B42. Convert it to the Lua-indexable
    -- array form used by vanilla for other Java collections.
    for _, vehicle in ipairs(vehicles:toArray()) do
        if isCar(vehicle) and inSupportArea(outpost, vehicle) then
            candidates = candidates + 1
            local facts = Inspector.inspect(vehicle)
            local failures = evaluate(facts)
            if not bestFailures or #failures < #bestFailures then
                bestFacts, bestFailures = facts, failures
            end
        end
    end

    local fullyLoaded = supportAreaFullyLoaded(outpost)
    -- One qualifying car is conclusive even if a farther support chunk has not
    -- streamed yet. A negative or failing result is only conclusive once all
    -- chunks in the support area are available.
    if not (bestFacts and #bestFailures == 0) and not fullyLoaded then
        return { available = false, passed = false, current = 0, required = 0 }
    end

    if not bestFacts then
        return { available = true, passed = false, current = 0, required = 0, state = "none" }
    end
    local state = "requirements_unmet"
    if #bestFailures == 0 then
        state = "ready"
    elseif #bestFailures == 1 and bestFailures[1] == "fuel" then
        state = "needs_fuel"
    elseif #bestFailures == 1 and bestFailures[1] == "battery_charge" then
        state = "needs_battery_charge"
    elseif #bestFailures == 1 and bestFailures[1] == "battery" then
        state = "needs_battery"
    elseif #bestFailures == 1 and bestFailures[1] == "tyres" then
        state = "needs_tyres"
    elseif #bestFailures == 1 and bestFailures[1] == "driver_seat" then
        state = "needs_driver_seat"
    end
    return {
        available = true,
        passed = #bestFailures == 0,
        current = #bestFailures,
        required = 0,
        state = state,
        fingerprint = Inspector.fingerprint(bestFacts),
        details = { candidateCount = candidates, vehicle = bestFacts, failures = bestFailures },
    }
end

Check.requirements = REQUIREMENTS
Check.evaluate = evaluate
Check.inSupportArea = inSupportArea
Check.supportAreaFullyLoaded = supportAreaFullyLoaded
Check.isCar = isCar
Check.inspect = Inspector.inspect
function Check.hasRequiredLatchState(vehicle)
    if not isCar(vehicle) then return false end
    local facts = Inspector.inspect(vehicle)
    return facts ~= nil
        and facts.engine.installed == true
        and facts.fuel.installed == true
        and facts.fuel.currentRounded > 0
        and facts.battery.installed == true
        and facts.driverSeat.installed == true
        and hasAllTyresInstalled(facts)
end
function Check.findBySqlId(sqlId)
    local cell = getCell and getCell() or nil
    local vehicles = cell and cell:getVehicles() or nil
    if not vehicles then return nil end
    local wanted = tostring(sqlId)
    for _, vehicle in ipairs(vehicles:toArray()) do
        if tostring(vehicle:getSqlId()) == wanted then return vehicle end
    end
    return nil
end
function Check.qualifies(vehicle)
    if not isCar(vehicle) then return false end
    local facts = Inspector.inspect(vehicle)
    return facts ~= nil and #evaluate(facts) == 0
end
function Check.qualifiesSuccessfulStart(vehicle)
    if not isCar(vehicle) then return false end
    local facts = Inspector.inspect(vehicle)
    if not facts then return false end
    -- The starter has already consumed 2.5% charge by the time Running is
    -- observable. A successful transition itself proves that the pre-crank
    -- battery requirement was met, so only that post-start failure is ignored.
    for _, failure in ipairs(evaluate(facts)) do
        if failure ~= "battery_charge" then return false end
    end
    return true
end
Outposts.addCheck("spare_car", vehicleResult, 100)

return Check
