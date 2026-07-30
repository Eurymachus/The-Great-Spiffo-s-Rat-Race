local MilkSnapshot = {}

function MilkSnapshot.copy(values)
    local result = {}
    for milkType, amount in pairs(values or {}) do
        amount = math.max(0, tonumber(amount) or 0)
        if amount > 0 then result[tostring(milkType)] = amount end
    end
    return result
end

function MilkSnapshot.list(values)
    local result = {}
    for milkType, amount in pairs(MilkSnapshot.copy(values)) do
        result[#result + 1] = {
            milkType = milkType,
            amount = amount,
        }
    end
    table.sort(result, function(a, b)
        return a.milkType < b.milkType
    end)
    return result
end

return MilkSnapshot
