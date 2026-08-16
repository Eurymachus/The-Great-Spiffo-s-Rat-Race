local ProgressWeights = {}

ProgressWeights.CATEGORIES = {
    kills = 2,
    outposts = 1,
    skills = 1,
}

function ProgressWeights.calculate(records)
    local weightedTotal = 0
    local appliedWeight = 0
    for _, record in ipairs(records or {}) do
        local weight = ProgressWeights.CATEGORIES[record.id]
        if weight and not record.optional and record.available ~= false then
            local percent = math.max(0, math.min(100,
                tonumber(record.percent) or 0))
            weightedTotal = weightedTotal + percent * weight
            appliedWeight = appliedWeight + weight
        end
    end
    return appliedWeight > 0 and weightedTotal / appliedWeight or 0
end

return ProgressWeights
