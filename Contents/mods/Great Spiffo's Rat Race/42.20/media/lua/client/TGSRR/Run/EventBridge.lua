local ChallengeEvents = require "TGSRR/Core/Events"
local Completion = require "TGSRR/Outposts/Completion"
local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"

local EventBridge = {}
local installed = false

local function record(eventType, payload)
    local ok, result = Recorder.record(eventType, payload)
    if not ok and result ~= "recorder_inactive" then
        print("[TGSRR Run] Event bridge rejected " .. tostring(eventType)
            .. ": " .. tostring(result))
    end
    return ok, result
end

local function deliverableValue(value)
    value = type(value) == "table" and value or {}
    return {
        current = tonumber(value.current) or 0,
        required = tonumber(value.required) or 0,
        state = value.state and tostring(value.state) or nil,
    }
end

local function lifecycleSummary(run, outpostId, deliverableId)
    if type(run.outpostLifecycles) ~= "table" then
        run.outpostLifecycles = { outposts = {}, deliverables = {} }
    end
    local root = run.outpostLifecycles
    if type(root.outposts) ~= "table" then root.outposts = {} end
    if type(root.deliverables) ~= "table" then root.deliverables = {} end
    local entries = root.outposts
    local key = outpostId
    if deliverableId then
        entries = root.deliverables
        key = outpostId .. "\0" .. deliverableId
    end
    if type(entries[key]) ~= "table" then
        entries[key] = { completionCount = 0, regressionCount = 0 }
    end
    return entries[key]
end

local function point(run, value)
    local gameTime = getGameTime and getGameTime() or nil
    local worldAge = gameTime and gameTime:getWorldAgeHours() or 0
    local result = {
        utc = Identity.utcSeconds(),
        worldAgeHours = worldAge,
        elapsedDays = math.max(0,
            (worldAge - (tonumber(run.createdWorldAgeHours) or 0)) / 24),
    }
    if value then
        local observed = deliverableValue(value)
        result.current = observed.current
        result.required = observed.required
        result.state = observed.state
    end
    return result
end

local function observeLifecycle(completed, event)
    local run = Recorder.getActiveRun()
    if type(run) ~= "table" then return end
    local outpostId = tostring(event.outpostId or "unknown")
    local deliverableId = event.deliverableId
        and tostring(event.deliverableId) or nil
    local summary = lifecycleSummary(run, outpostId, deliverableId)
    local observed = point(run, deliverableId and event.current or nil)
    if completed then
        summary.completionCount = math.max(0,
            math.floor(tonumber(summary.completionCount) or 0)) + 1
        if not summary.firstCompletion then
            local eventType, payload
            if deliverableId then
                eventType = "outpost.deliverable.completed"
                payload = {
                    outpostId = outpostId,
                    deliverableId = deliverableId,
                    value = deliverableValue(event.current),
                }
            else
                eventType = "outpost.completed"
                local completion = Completion.calculate(event.record)
                payload = {
                    outpostId = outpostId,
                    passedRequirements = completion.passedRequirements,
                    totalRequirements = completion.totalRequirements,
                    percent = completion.percent,
                }
            end
            local ok, recorded = record(eventType, payload)
            if not ok then return end
            observed.sequence = recorded.sequence
            observed.utc = recorded.utc
            observed.worldAgeHours = recorded.worldAgeHours
            observed.elapsedDays = math.max(0,
                (recorded.worldAgeHours
                    - (tonumber(run.createdWorldAgeHours) or 0)) / 24)
            summary.firstCompletion = observed
        end
        summary.latestCompletion = observed
    else
        summary.regressionCount = math.max(0,
            math.floor(tonumber(summary.regressionCount) or 0)) + 1
        summary.latestRegression = observed
    end
end

function EventBridge.install()
    if installed then return end
    installed = true
    ChallengeEvents.subscribe("kills.milestone.reached", "run_history:kills", function(event)
        record("kills.milestone.reached", {
            threshold = tonumber(event.threshold) or 0,
            previous = tonumber(event.previous) or 0,
            current = tonumber(event.current) or 0,
            characterId = tostring(event.characterId or "player"),
        })
    end)
    ChallengeEvents.subscribe("skill.level.reached", "run_history:skill_level", function(event)
        record("skill.level.reached", {
            skillId = tostring(event.skillId or "unknown"),
            categoryId = event.categoryId and tostring(event.categoryId) or nil,
            level = tonumber(event.level) or 0,
        })
    end)
    ChallengeEvents.subscribe("outpost.deliverable.completed",
        "run_history:outpost_deliverable", function(event)
            observeLifecycle(true, event)
        end)
    ChallengeEvents.subscribe("outpost.deliverable.regressed",
        "run_history:outpost_deliverable_regression", function(event)
            observeLifecycle(false, event)
        end)
    ChallengeEvents.subscribe("outpost.completed", "run_history:outpost",
        function(event) observeLifecycle(true, event) end)
    ChallengeEvents.subscribe("outpost.regressed", "run_history:outpost_regression",
        function(event) observeLifecycle(false, event) end)
end

return EventBridge
