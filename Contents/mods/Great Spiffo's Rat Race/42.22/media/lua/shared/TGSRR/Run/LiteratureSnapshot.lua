local LiteratureSnapshot = {}

local function copySorted(values)
    local result = {}
    for _, value in ipairs(values or {}) do
        result[#result + 1] = tostring(value)
    end
    table.sort(result)
    return result
end

local function union(values, additions)
    local seen = {}
    for _, value in ipairs(values) do seen[value] = true end
    for _, value in ipairs(additions or {}) do
        value = tostring(value)
        if value ~= "" and not seen[value] then
            seen[value] = true
            values[#values + 1] = value
        end
    end
    table.sort(values)
end

function LiteratureSnapshot.observe(run)
    local state = type(run) == "table" and run.literature or nil
    local baseline = state and state.baseline or {}
    local baselineIds = copySorted(baseline.itemIds)
    local baselineSet = {}
    for _, id in ipairs(baselineIds) do baselineSet[id] = true end

    local items = {}
    local currentIds = copySorted(baselineIds)
    for id, record in pairs(state and state.completed or {}) do
        id = tostring(id)
        items[#items + 1] = {
            id = id,
            classification = tostring(record.classification or "literature"),
            baseline = baselineSet[id] == true,
            completions = math.max(0, math.floor(tonumber(record.completions) or 0)),
            firstCompletionUtc =
                math.max(0, math.floor(tonumber(record.firstCompletionUtc) or 0)),
            firstCompletionWorldAgeHours =
                math.max(0, tonumber(record.firstCompletionWorldAgeHours) or 0),
            lastCompletionUtc =
                math.max(0, math.floor(tonumber(record.lastCompletionUtc) or 0)),
            lastCompletionWorldAgeHours =
                math.max(0, tonumber(record.lastCompletionWorldAgeHours) or 0),
            learnedRecipeIds = copySorted(record.learnedRecipeIds),
            literatureTitles = copySorted(record.literatureTitles),
            printMediaIds = copySorted(record.printMediaIds),
        }
        if not baselineSet[id] then currentIds[#currentIds + 1] = id end
    end
    table.sort(items, function(a, b) return a.id < b.id end)
    table.sort(currentIds)

    local printMediaIds = copySorted(baseline.printMediaIds)
    local literatureTitles = copySorted(baseline.literatureTitles)
    for _, record in ipairs(items) do
        union(printMediaIds, record.printMediaIds)
        union(literatureTitles, record.literatureTitles)
    end

    return {
        schema = 1,
        partial = not state or state.partial == true,
        baseline = {
            capturedUtc =
                math.max(0, math.floor(tonumber(baseline.capturedUtc) or 0)),
            worldAgeHours =
                math.max(0, tonumber(baseline.worldAgeHours) or 0),
            itemIds = baselineIds,
            literatureTitles = copySorted(baseline.literatureTitles),
            printMediaIds = copySorted(baseline.printMediaIds),
        },
        currentItemIds = currentIds,
        currentLiteratureTitles = literatureTitles,
        currentPrintMediaIds = printMediaIds,
        completed = items,
    }
end

return LiteratureSnapshot
