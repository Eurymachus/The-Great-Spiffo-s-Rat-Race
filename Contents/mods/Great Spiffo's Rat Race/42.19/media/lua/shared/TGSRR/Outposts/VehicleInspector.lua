local Inspector = {}

local function percent(current, capacity)
    if not capacity or capacity <= 0 then return 0 end
    return math.max(0, math.min(100, current / capacity * 100))
end

local function partFacts(part)
    local item = part:getInventoryItem()
    return {
        id = part:getId(),
        installed = not part:isInventoryItemUninstalled(),
        condition = part:getCondition(),
        wheelIndex = part:getWheelIndex(),
        content = part:getContainerContentAmount(),
        capacity = part:getContainerCapacity(),
        itemType = item and item:getFullType() or nil,
    }
end

function Inspector.inspect(vehicle)
    if not vehicle then return nil end
    local result = {
        sqlId = vehicle:getSqlId(),
        scriptName = vehicle:getScriptName(),
        x = vehicle:getX(),
        y = vehicle:getY(),
        engineQuality = vehicle:getEngineQuality(),
        parts = {},
        tyres = {},
        seats = {},
    }

    for index = 0, vehicle:getPartCount() - 1 do
        local part = vehicle:getPartByIndex(index)
        local facts = partFacts(part)
        result.parts[facts.id] = facts
        if facts.wheelIndex >= 0 then
            facts.pressure = facts.content
            facts.maximumPressure = facts.capacity
            facts.pressurePercent = percent(facts.content, facts.capacity)
            result.tyres[#result.tyres + 1] = facts
        end
    end

    local engine = vehicle:getPartById("Engine")
    result.engine = engine and partFacts(engine) or { id = "Engine", installed = false, condition = 0 }

    local tank = vehicle:getPartById("GasTank")
    result.fuel = tank and {
        installed = not tank:isInventoryItemUninstalled(),
        current = tank:getContainerContentAmount(),
        capacity = tank:getContainerCapacity(),
        percent = percent(tank:getContainerContentAmount(), tank:getContainerCapacity()),
        condition = tank:getCondition(),
    } or { installed = false, current = 0, capacity = 0, percent = 0, condition = 0 }

    local battery = vehicle:getBattery()
    result.battery = battery and {
        installed = not battery:isInventoryItemUninstalled(),
        condition = battery:getCondition(),
        charge = math.max(0, math.min(100, vehicle:getBatteryCharge() * 100)),
    } or { installed = false, condition = 0, charge = 0 }

    for seat = 0, vehicle:getMaxPassengers() - 1 do
        local part = vehicle:getPartForSeatContainer(seat)
        result.seats[#result.seats + 1] = {
            passengerIndex = seat,
            role = seat == 0 and "driver" or "passenger",
            partId = part and part:getId() or nil,
            installed = part ~= nil and not part:isInventoryItemUninstalled(),
            condition = part and part:getCondition() or 0,
        }
    end
    result.driverSeat = result.seats[1] or {
        passengerIndex = 0, role = "driver", installed = false, condition = 0,
    }
    return result
end

function Inspector.fingerprint(result)
    if not result then return "" end
    local function rounded(value)
        return tostring(math.floor((value or 0) + 0.5))
    end
    local values = {
        tostring(result.sqlId), tostring(result.scriptName),
        rounded(result.engine.condition), rounded(result.fuel.percent),
        rounded(result.battery.condition), rounded(result.battery.charge),
        tostring(result.driverSeat.installed), rounded(result.driverSeat.condition),
    }
    for _, tyre in ipairs(result.tyres) do
        values[#values + 1] = table.concat({ tyre.id, tostring(tyre.installed),
            rounded(tyre.condition), rounded(tyre.pressurePercent) }, ":")
    end
    return table.concat(values, "|")
end

return Inspector
