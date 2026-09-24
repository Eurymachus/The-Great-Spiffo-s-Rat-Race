local FluidConsumedSnapshot = {}

function FluidConsumedSnapshot.copy(values)
    local result = {}
    for fluidTypeId, amount in pairs(values or {}) do
        amount = math.max(0, tonumber(amount) or 0)
        if amount > 0 then result[tostring(fluidTypeId)] = amount end
    end
    return result
end

function FluidConsumedSnapshot.list(values)
    local result = {}
    for fluidTypeId, amount in pairs(
            FluidConsumedSnapshot.copy(values)) do
        result[#result + 1] = {
            fluidTypeId = fluidTypeId,
            liters = amount,
        }
    end
    table.sort(result, function(a, b)
        return a.fluidTypeId < b.fluidTypeId
    end)
    return result
end

return FluidConsumedSnapshot
