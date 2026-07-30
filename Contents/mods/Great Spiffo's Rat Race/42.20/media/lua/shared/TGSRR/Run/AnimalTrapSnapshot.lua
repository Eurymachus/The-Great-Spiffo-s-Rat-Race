local AnimalTrapSnapshot = {}

local function positiveInteger(value)
    return math.max(0, math.floor(tonumber(value) or 0))
end

function AnimalTrapSnapshot.copy(values)
    local result = {}
    for animalType, traps in pairs(values or {}) do
        if type(traps) == "table" then
            local copied = {}
            for trapId, count in pairs(traps) do
                count = positiveInteger(count)
                if count > 0 then copied[tostring(trapId)] = count end
            end
            local hasValues = false
            for _ in pairs(copied) do
                hasValues = true
                break
            end
            if hasValues then result[tostring(animalType)] = copied end
        end
    end
    return result
end

function AnimalTrapSnapshot.pairs(values)
    local result = {}
    for animalType, traps in pairs(AnimalTrapSnapshot.copy(values)) do
        for trapId, count in pairs(traps) do
            result[#result + 1] = {
                animalType = animalType,
                trapId = trapId,
                trapped = count,
            }
        end
    end
    table.sort(result, function(a, b)
        if a.animalType ~= b.animalType then
            return a.animalType < b.animalType
        end
        return a.trapId < b.trapId
    end)
    return result
end

local function summary(values, sourceKey, outputKey)
    local totals = {}
    for _, pair in ipairs(AnimalTrapSnapshot.pairs(values)) do
        local id = pair[sourceKey]
        totals[id] = (totals[id] or 0) + pair.trapped
    end
    local result = {}
    for id, count in pairs(totals) do
        result[#result + 1] = {
            [outputKey] = id,
            trapped = count,
        }
    end
    table.sort(result, function(a, b)
        return a[outputKey] < b[outputKey]
    end)
    return result
end

function AnimalTrapSnapshot.animalTypes(values)
    return summary(values, "animalType", "animalType")
end

function AnimalTrapSnapshot.traps(values)
    return summary(values, "trapId", "trapId")
end

function AnimalTrapSnapshot.deltaPairs(current, baseline)
    local result = {}
    local keys = {}
    current = AnimalTrapSnapshot.copy(current)
    baseline = AnimalTrapSnapshot.copy(baseline)
    for animalType, traps in pairs(current) do
        keys[animalType] = keys[animalType] or {}
        for trapId in pairs(traps) do keys[animalType][trapId] = true end
    end
    for animalType, traps in pairs(baseline) do
        keys[animalType] = keys[animalType] or {}
        for trapId in pairs(traps) do keys[animalType][trapId] = true end
    end
    for animalType, traps in pairs(keys) do
        for trapId in pairs(traps) do
            local delta = positiveInteger(current[animalType]
                and current[animalType][trapId])
                - positiveInteger(baseline[animalType]
                    and baseline[animalType][trapId])
            if delta ~= 0 then
                result[#result + 1] = {
                    animalType = animalType,
                    trapId = trapId,
                    trapped = delta,
                }
            end
        end
    end
    table.sort(result, function(a, b)
        if a.animalType ~= b.animalType then
            return a.animalType < b.animalType
        end
        return a.trapId < b.trapId
    end)
    return result
end

return AnimalTrapSnapshot
