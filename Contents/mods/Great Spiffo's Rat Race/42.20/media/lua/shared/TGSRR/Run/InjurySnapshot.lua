local InjurySnapshot = {}

local SEPARATOR = "|"

function InjurySnapshot.key(injuryType, bodyPart)
    return tostring(injuryType) .. SEPARATOR .. tostring(bodyPart)
end

function InjurySnapshot.split(key)
    key = tostring(key or "")
    local separator = key:find(SEPARATOR, 1, true)
    if not separator then return key, "" end
    return key:sub(1, separator - 1), key:sub(separator + 1)
end

function InjurySnapshot.copy(values)
    local result = {}
    for key, count in pairs(values or {}) do
        count = math.max(0, math.floor(tonumber(count) or 0))
        if count > 0 then result[tostring(key)] = count end
    end
    return result
end

function InjurySnapshot.deltaPairs(current, baseline)
    local deltas = {}
    local keys = {}
    for key in pairs(current or {}) do keys[key] = true end
    for key in pairs(baseline or {}) do keys[key] = true end
    for key in pairs(keys) do
        local count = (tonumber(current[key]) or 0)
            - (tonumber(baseline[key]) or 0)
        if count ~= 0 then
            local injuryType, bodyPart = InjurySnapshot.split(key)
            deltas[#deltas + 1] = {
                injuryType = injuryType,
                bodyPart = bodyPart,
                count = count,
            }
        end
    end
    table.sort(deltas, function(a, b)
        if a.injuryType ~= b.injuryType then
            return a.injuryType < b.injuryType
        end
        return a.bodyPart < b.bodyPart
    end)
    return deltas
end

local function aggregate(values, dimension)
    local totals = {}
    for key, count in pairs(InjurySnapshot.copy(values)) do
        local injuryType, bodyPart = InjurySnapshot.split(key)
        local id = dimension == "bodyPart" and bodyPart or injuryType
        totals[id] = (totals[id] or 0) + count
    end
    local result = {}
    for id, count in pairs(totals) do
        result[#result + 1] = {
            id = id,
            count = count,
        }
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

function InjurySnapshot.observe(values, total)
    return {
        total = math.max(0, math.floor(tonumber(total) or 0)),
        byType = aggregate(values, "injuryType"),
        byBodyPart = aggregate(values, "bodyPart"),
        pairs = InjurySnapshot.deltaPairs(values, {}),
    }
end

return InjurySnapshot
