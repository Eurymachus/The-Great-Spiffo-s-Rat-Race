local WeaponKillSnapshot = {}

WeaponKillSnapshot.VEHICLE = "__VEHICLE__"
WeaponKillSnapshot.UNARMED = "__UNARMED__"
WeaponKillSnapshot.UNKNOWN = "__UNKNOWN__"

function WeaponKillSnapshot.copy(values)
    local result = {}
    for id, count in pairs(values or {}) do
        count = math.max(0, math.floor(tonumber(count) or 0))
        if count > 0 then result[tostring(id)] = count end
    end
    return result
end

function WeaponKillSnapshot.list(values)
    local result = {}
    for id, count in pairs(WeaponKillSnapshot.copy(values)) do
        result[#result + 1] = { id = id, kills = count }
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

function WeaponKillSnapshot.weaponId(weapon)
    if not weapon then return WeaponKillSnapshot.UNARMED end
    local fullType = weapon.getFullType and weapon:getFullType() or nil
    local itemType = weapon.getType and weapon:getType() or nil
    if fullType == "Base.BareHands" or itemType == "BareHands" then
        return WeaponKillSnapshot.UNARMED
    end
    if fullType and tostring(fullType) ~= "" then return tostring(fullType) end
    return WeaponKillSnapshot.UNKNOWN
end

return WeaponKillSnapshot
