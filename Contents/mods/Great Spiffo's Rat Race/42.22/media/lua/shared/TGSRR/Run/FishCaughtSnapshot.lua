local FishCaughtSnapshot = {}

function FishCaughtSnapshot.copy(values)
    local result = {}
    for fishId, count in pairs(values or {}) do
        count = math.max(0, math.floor(tonumber(count) or 0))
        if count > 0 then result[tostring(fishId)] = count end
    end
    return result
end

function FishCaughtSnapshot.list(values)
    local result = {}
    for fishId, count in pairs(FishCaughtSnapshot.copy(values)) do
        result[#result + 1] = {
            fishId = fishId,
            caught = count,
        }
    end
    table.sort(result, function(a, b) return a.fishId < b.fishId end)
    return result
end

return FishCaughtSnapshot
