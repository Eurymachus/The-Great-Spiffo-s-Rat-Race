local ChallengeEvents = require "TGSRR/Core/Events"
local Completion = require "TGSRR/Outposts/Completion"
local Recorder = require "TGSRR/Run/Recorder"

local EventBridge = {}
local installed = false

local function record(eventType, payload)
    local ok, err = Recorder.record(eventType, payload)
    if not ok and err ~= "recorder_inactive" then
        print("[TGSRR Run] Event bridge rejected " .. tostring(eventType) .. ": " .. tostring(err))
    end
end

local function deliverableValue(value)
    value = type(value) == "table" and value or {}
    return {
        current = tonumber(value.current) or 0,
        required = tonumber(value.required) or 0,
        state = value.state and tostring(value.state) or nil,
    }
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

    ChallengeEvents.subscribe("outpost.deliverable.completed", "run_history:outpost_deliverable", function(event)
        record("outpost.deliverable.completed", {
            outpostId = tostring(event.outpostId or "unknown"),
            deliverableId = tostring(event.deliverableId or "unknown"),
            value = deliverableValue(event.current),
        })
    end)

    ChallengeEvents.subscribe("outpost.completed", "run_history:outpost", function(event)
        local completion = Completion.calculate(event.record)
        record("outpost.completed", {
            outpostId = tostring(event.outpostId or "unknown"),
            passedRequirements = completion.passedRequirements,
            totalRequirements = completion.totalRequirements,
            percent = completion.percent,
        })
    end)
end

return EventBridge
