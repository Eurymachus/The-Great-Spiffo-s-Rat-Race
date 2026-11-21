local CookedFoodSnapshot = {}

function CookedFoodSnapshot.copy(values)
    local result = {}
    for id, count in pairs(values or {}) do
        if count > 0 then result[id] = count end
    end
    return result
end

function CookedFoodSnapshot.observe(run)
    local state = run and run.cookedFood
    if not state then return nil end
    return {
        schema = 1,
        items = CookedFoodSnapshot.copy(state.items),
        partial = state.partial == true or nil,
    }
end

return CookedFoodSnapshot
