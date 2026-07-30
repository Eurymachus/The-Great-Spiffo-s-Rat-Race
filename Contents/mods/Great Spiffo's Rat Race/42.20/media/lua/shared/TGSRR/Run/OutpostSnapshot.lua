local Outposts = require "TGSRR/Outposts/Definitions"
local Store = require "TGSRR/Outposts/ProgressStore"
local Completion = require "TGSRR/Outposts/Completion"

local OutpostSnapshot = {}

local function stage(record, complete)
    if record.discovered ~= true then return "undiscovered" end
    if complete then return "complete" end
    if record.progressStage and record.progressStage.workStarted == true then
        return "in_progress"
    end
    return "discovered"
end

local function deliverableSnapshot(record, completion)
    local result = {}
    for id, value in pairs(record.deliverables or {}) do
        result[#result + 1] = {
            id = tostring(id),
            available = value.available == true,
            passed = value.passed == true,
            current = tonumber(value.current) or 0,
            required = tonumber(value.required) or 0,
            state = value.state and tostring(value.state) or nil,
            progress = math.max(0, math.min(1,
                tonumber(completion.fractions[id]) or 0)),
            observedWorldAgeHours = tonumber(value.observedAt) or 0,
        }
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

function OutpostSnapshot.observe()
    local result = {}
    for _, definition in ipairs(Outposts.getAll()) do
        local record = Store.get(definition.id)
        local completion = Completion.calculate(record)
        local progressStage = record.progressStage or {}
        result[#result + 1] = {
            id = definition.id,
            discovered = record.discovered == true,
            discoveredWorldAgeHours = tonumber(record.discoveredAt) or 0,
            stage = stage(record, completion.complete),
            complete = completion.complete == true,
            progress = completion.progress,
            passedRequirements = completion.passedRequirements,
            totalRequirements = completion.totalRequirements,
            workStartedWorldAgeHours = tonumber(progressStage.startedAt) or 0,
            deliverables = deliverableSnapshot(record, completion),
        }
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

return OutpostSnapshot
