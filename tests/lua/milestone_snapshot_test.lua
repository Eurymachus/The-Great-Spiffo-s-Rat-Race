package.loaded["TGSRR/Run/EventCodec"] = {
    inspectBody = function(body)
        return body
    end,
    decodePayload = function(payload)
        return payload
    end,
}

local MilestoneSnapshot = require "TGSRR/Run/MilestoneSnapshot"

local function record(sequence, skillId, categoryId, level)
    return {
        body = {
            eventType = "skill.level.reached",
            sequence = sequence,
            utc = 1000 + sequence,
            worldAgeHours = 24 + sequence,
            canonicalPayload = {
                skillId = skillId,
                categoryId = categoryId,
                level = level,
            },
        },
    }
end

local result, err = MilestoneSnapshot.observe({
    createdWorldAgeHours = 24,
    bootstrapped = false,
}, {
    record(1, "Fitness", "Passive", 9),
    record(2, "Axe", "Combat", 10),
    record(3, "Fitness", "Passive", 10),
    record(4, "Axe", "Combat", 10),
    record(5, "Sprinting", "Agility", 11),
})

assert(result, err)
assert(result.partial == false)
assert(#result.skillMilestones == 2)
assert(result.skillMilestones[1].skillId == "Axe")
assert(result.skillMilestones[1].categoryId == "Combat")
assert(result.skillMilestones[1].level == 10)
assert(result.skillMilestones[1].completionOrder == 1)
assert(result.skillMilestones[1].sequence == 2)
assert(result.skillMilestones[1].elapsedDays == 2 / 24)
assert(result.skillMilestones[2].skillId == "Fitness")
assert(result.skillMilestones[2].completionOrder == 2)
assert(result.skillMilestones[2].sequence == 3)

local partial = MilestoneSnapshot.observe({
    createdWorldAgeHours = 0,
    bootstrapped = true,
}, {})
assert(partial.partial == true)

print("milestone snapshot test passed")
