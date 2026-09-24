local BrokenWeaponSnapshot = {}

function BrokenWeaponSnapshot.copy(values)
    local result = {}
    for id, count in pairs(values or {}) do
        count = math.max(0, math.floor(tonumber(count) or 0))
        if count > 0 then result[tostring(id)] = count end
    end
    return result
end

function BrokenWeaponSnapshot.list(values)
    local result = {}
    for id, count in pairs(BrokenWeaponSnapshot.copy(values)) do
        result[#result + 1] = { id = id, breaks = count }
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

return BrokenWeaponSnapshot
