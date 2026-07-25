local ModSnapshot = {}

function ModSnapshot.observe()
    local result = {}
    local mods = getActivatedMods and getActivatedMods() or nil
    if not mods then return result end
    for index = 0, mods:size() - 1 do
        local modId = tostring(mods:get(index))
        local modInfo = getModInfoByID and getModInfoByID(modId) or nil
        local workshopId = modInfo and modInfo.getWorkshopID
            and modInfo:getWorkshopID() or nil
        result[#result + 1] = {
            modId = modId,
            workshopId = workshopId and tostring(workshopId) or "",
        }
    end
    table.sort(result, function(a, b) return a.modId < b.modId end)
    return result
end

function ModSnapshot.ids(mods)
    local modIds, workshopIds, workshopSet = {}, {}, {}
    for _, reference in ipairs(mods or {}) do
        modIds[#modIds + 1] = reference.modId
        if reference.workshopId ~= "" and not workshopSet[reference.workshopId] then
            workshopSet[reference.workshopId] = true
            workshopIds[#workshopIds + 1] = reference.workshopId
        end
    end
    table.sort(modIds)
    table.sort(workshopIds)
    return modIds, workshopIds
end

return ModSnapshot
