local EventCodec = require "TGSRR/Run/EventCodec"

local MilestoneSnapshot = {}

local function nonNegative(value)
    return math.max(0, tonumber(value) or 0)
end

local function timing(run, event)
    local started = tonumber(run and run.createdWorldAgeHours) or 0
    local worldAge = nonNegative(event.worldAgeHours)
    return {
        sequence = math.max(0, math.floor(tonumber(event.sequence) or 0)),
        utc = math.max(0, math.floor(tonumber(event.utc) or 0)),
        worldAgeHours = worldAge,
        elapsedDays = math.max(0, (worldAge - started) / 24),
    }
end

local function eventFromRecord(record)
    local event, inspectError = EventCodec.inspectBody(record and record.body)
    if not event then return nil, inspectError end
    local payload, payloadError =
        EventCodec.decodePayload(event.canonicalPayload)
    if not payload then return nil, payloadError end
    event.payload = payload
    return event
end

local function appendTiming(target, run, event)
    local observed = timing(run, event)
    for key, value in pairs(observed) do target[key] = value end
    return target
end

function MilestoneSnapshot.observe(run, records)
    local result = {
        schema = 1,
        partial = type(run) ~= "table" or run.bootstrapped == true,
        outpostCompletions = {},
        killMilestones = {},
        skillMilestones = {},
        outpostDeliverableMilestones = {},
    }
    local completedOutposts = {}
    local completedDeliverables = {}
    local completedSkills = {}

    for _, record in ipairs(records or {}) do
        local event, eventError = eventFromRecord(record)
        if not event then return nil, eventError end
        local payload = event.payload

        if event.eventType == "outpost.completed" then
            local outpostId = tostring(payload.outpostId or "")
            if outpostId ~= "" and not completedOutposts[outpostId] then
                completedOutposts[outpostId] = true
                result.outpostCompletions[#result.outpostCompletions + 1] =
                    appendTiming({
                        outpostId = outpostId,
                        completionOrder = #result.outpostCompletions + 1,
                        passedRequirements = math.max(0,
                            math.floor(tonumber(payload.passedRequirements) or 0)),
                        totalRequirements = math.max(0,
                            math.floor(tonumber(payload.totalRequirements) or 0)),
                        progress = math.max(0, math.min(1,
                            (tonumber(payload.percent) or 0) / 100)),
                    }, run, event)
            end
        elseif event.eventType == "kills.milestone.reached" then
            result.killMilestones[#result.killMilestones + 1] =
                appendTiming({
                    threshold = math.max(0,
                        math.floor(tonumber(payload.threshold) or 0)),
                    killTotal = math.max(0,
                        math.floor(tonumber(payload.current) or 0)),
                    characterId = tostring(payload.characterId or "player"),
                }, run, event)
        elseif event.eventType == "skill.level.reached" then
            local skillId = tostring(payload.skillId or "")
            local level = math.max(0,
                math.floor(tonumber(payload.level) or 0))
            if skillId ~= "" and level == 10
                    and not completedSkills[skillId] then
                completedSkills[skillId] = true
                result.skillMilestones[#result.skillMilestones + 1] =
                    appendTiming({
                        skillId = skillId,
                        categoryId = payload.categoryId
                            and tostring(payload.categoryId) or nil,
                        level = level,
                        completionOrder = #result.skillMilestones + 1,
                    }, run, event)
            end
        elseif event.eventType == "outpost.deliverable.completed" then
            local outpostId = tostring(payload.outpostId or "")
            local deliverableId = tostring(payload.deliverableId or "")
            local key = outpostId .. "\0" .. deliverableId
            if outpostId ~= "" and deliverableId ~= ""
                    and not completedDeliverables[key] then
                completedDeliverables[key] = true
                local value = type(payload.value) == "table"
                    and payload.value or {}
                result.outpostDeliverableMilestones[
                    #result.outpostDeliverableMilestones + 1] =
                    appendTiming({
                        outpostId = outpostId,
                        deliverableId = deliverableId,
                        current = tonumber(value.current) or 0,
                        required = tonumber(value.required) or 0,
                        state = value.state and tostring(value.state) or nil,
                    }, run, event)
            end
        end
    end

    table.sort(result.killMilestones, function(a, b)
        if a.sequence ~= b.sequence then return a.sequence < b.sequence end
        return a.threshold < b.threshold
    end)
    return result
end

return MilestoneSnapshot
