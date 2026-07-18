local Registry = require "TGSRR/MilestoneRegistry"

local Milestones = {}
Milestones.killThresholds = { 1000, 10000, 25000, 50000, 100000, 250000, 500000, 750000, 1000000 }

Registry.register({
    id = "outpost.deliverable.complete",
    event = "outpost.deliverable.completed",
    claimKey = function(event)
        return "outpost.deliverable:" .. tostring(event.outpostId) .. ":" .. tostring(event.deliverableId)
    end,
    notificationKey = "UI_TGSRR_Milestone_OutpostDeliverable",
    notificationFallback = "Outpost requirement completed",
})

Registry.register({
    id = "outpost.complete",
    event = "outpost.completed",
    claimKey = function(event) return "outpost.complete:" .. tostring(event.outpostId) end,
    notificationKey = "UI_TGSRR_Milestone_OutpostComplete",
    notificationFallback = "Outpost completed",
})

for index, threshold in ipairs(Milestones.killThresholds) do
    Registry.register({
        id = "kills." .. tostring(threshold),
        event = "kills.milestone.reached",
        order = index,
        threshold = threshold,
        matches = function(event) return event.threshold == threshold end,
        claimKey = function(event)
            return "character:" .. tostring(event.characterId or "player") .. ":kills:" .. tostring(threshold)
        end,
        notificationKey = "UI_TGSRR_Milestone_KillsReached",
        notificationFallback = "Zombie kill milestone reached",
    })
end

return Milestones
