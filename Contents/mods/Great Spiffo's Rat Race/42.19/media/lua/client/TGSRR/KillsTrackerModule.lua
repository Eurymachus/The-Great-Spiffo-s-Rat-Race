local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local KillsData = require "TGSRR/KillsTrackerData"
local KillsView = require "TGSRR/KillsTrackerView"

Deliverables.register({
    id = "kills",
    label = "Zombie Kills",
    order = 10,
    refreshRecord = function(context)
        KillsData.refresh(context.player)
    end,
    getRecord = function(context)
        return KillsData.getRecord(context.player)
    end,
})

Tracker.registerModule({
    id = "kills",
    title = "Kills",
    order = 20,
    createView = function(parent, x, y, width, height)
        return KillsView:new(x, y, width, height)
    end,
})

return Tracker.getModule("kills")
