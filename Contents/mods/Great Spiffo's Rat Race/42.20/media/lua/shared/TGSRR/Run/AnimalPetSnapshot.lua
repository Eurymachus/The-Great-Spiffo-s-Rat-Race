local AnimalPetSnapshot = {}

function AnimalPetSnapshot.copy(values)
    local result = {}
    for animalType, count in pairs(values or {}) do
        count = math.max(0, math.floor(tonumber(count) or 0))
        if count > 0 then result[tostring(animalType)] = count end
    end
    return result
end

function AnimalPetSnapshot.list(values)
    local result = {}
    for animalType, count in pairs(AnimalPetSnapshot.copy(values)) do
        result[#result + 1] = {
            animalType = animalType,
            pets = count,
        }
    end
    table.sort(result, function(a, b)
        return a.animalType < b.animalType
    end)
    return result
end

return AnimalPetSnapshot
