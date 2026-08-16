local Outposts = require "TGSRR/Outposts/Definitions"
local Store = require "TGSRR/Outposts/ProgressStore"
local Completion = require "TGSRR/Outposts/Completion"

local OutpostSnapshot = {}

local function hasLifecycleHistory(summary)
    if type(summary) ~= "table" then return false end
    return (tonumber(summary.completionCount) or 0) > 0
        or (tonumber(summary.regressionCount) or 0) > 0
        or type(summary.firstCompletion) == "table"
        or type(summary.latestCompletion) == "table"
        or type(summary.latestRegression) == "table"
end

local function hasObservation(value)
    if type(value) ~= "table" then return false end
    return value.available == true
        or value.passed == true
        or (tonumber(value.observedAt) or 0) > 0
        or (tonumber(value.current) or 0) ~= 0
        or (tonumber(value.required) or 0) ~= 0
        or (value.state ~= nil and tostring(value.state) ~= "")
        or (value.fingerprint ~= nil and tostring(value.fingerprint) ~= "")
end

local function stage(record, complete)
    if record.discovered ~= true then return "undiscovered" end
    if complete then return "complete" end
    if record.progressStage and record.progressStage.workStarted == true then
        return "in_progress"
    end
    return "discovered"
end

local function lifecycle(summary, complete)
    summary = summary or {}
    return {
        firstCompletion = summary.firstCompletion,
        latestCompletion = summary.latestCompletion,
        latestRegression = summary.latestRegression,
        completionCount = math.max(0,
            math.floor(tonumber(summary.completionCount) or 0)),
        regressionCount = math.max(0,
            math.floor(tonumber(summary.regressionCount) or 0)),
        currentState = complete and "complete" or "incomplete",
    }
end

local function deliverableSnapshot(outpostId, record, completion, summaries)
    local result = {}
    for _, id in ipairs(Completion.getDeliverableIds()) do
        local value = (record.deliverables or {})[id]
        local summary = summaries[outpostId .. "\0" .. id]
        if hasObservation(value) or hasLifecycleHistory(summary) then
        value = value or {}
        local complete = value.passed == true
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
            lifecycle = lifecycle(
                summary, complete),
        }
        end
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

function OutpostSnapshot.observe(lifecycles)
    lifecycles = lifecycles or { outposts = {}, deliverables = {} }
    local result = {}
    for _, definition in ipairs(Outposts.getAll()) do
        local record = Store.get(definition.id)
        if record.discovered == true then
        local summary = lifecycles.outposts[definition.id]
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
            lifecycle = lifecycle(
                summary, completion.complete),
            deliverables = deliverableSnapshot(definition.id, record, completion,
                lifecycles.deliverables or {}),
        }
        end
    end
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

return OutpostSnapshot
