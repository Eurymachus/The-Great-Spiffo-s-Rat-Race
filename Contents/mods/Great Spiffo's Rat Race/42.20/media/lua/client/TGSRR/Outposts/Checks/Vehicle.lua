local Outposts = require "TGSRR/Outposts/Definitions"
local Inspector = require "TGSRR/Outposts/VehicleInspector"

local Check = {}

-- Provisional first consumer of the generic inspector. These remain deliberately
-- centralized so a run definition can replace them without changing inspection.
local REQUIREMENTS = {
    engineCondition = 75,
    fuelPercent = 75,
    batteryCondition = 75,
    batteryCharge = 75,
    driverSeatCondition = 75,
    tyreCondition = 75,
    tyrePressurePercent = 75,
}

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
    requireFact(facts.engine.installed and facts.engine.condition >= REQUIREMENTS.engineCondition, "engine")
    requireFact(facts.fuel.installed and facts.fuel.percent >= REQUIREMENTS.fuelPercent, "fuel")
    requireFact(facts.battery.installed and facts.battery.condition >= REQUIREMENTS.batteryCondition, "battery_condition")
    requireFact(facts.battery.installed and facts.battery.charge >= REQUIREMENTS.batteryCharge, "battery_charge")
    requireFact(facts.driverSeat.installed and facts.driverSeat.condition >= REQUIREMENTS.driverSeatCondition, "driver_seat")
    requireFact(#facts.tyres > 0, "tyres")
    for _, tyre in ipairs(facts.tyres) do
        requireFact(tyre.installed and tyre.condition >= REQUIREMENTS.tyreCondition,
            "tyre_condition:" .. tyre.id)
        requireFact(tyre.installed and tyre.pressurePercent >= REQUIREMENTS.tyrePressurePercent,
            "tyre_pressure:" .. tyre.id)
    end
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
    return {
        available = true,
        passed = #bestFailures == 0,
        current = #bestFailures,
        required = 0,
        state = #bestFailures == 0 and "ready" or "requirements_unmet",
        fingerprint = Inspector.fingerprint(bestFacts),
        details = { candidateCount = candidates, vehicle = bestFacts, failures = bestFailures },
    }
end

Check.requirements = REQUIREMENTS
Check.evaluate = evaluate
Outposts.addCheck("spare_car", vehicleResult, 100)

return Check
