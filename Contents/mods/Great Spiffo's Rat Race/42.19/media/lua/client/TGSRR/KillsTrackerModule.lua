local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local KillsData = require "TGSRR/KillsTrackerData"
local KillsView = require "TGSRR/KillsTrackerView"
local L = require "TGSRR/Localization"

Deliverables.register({
    id = "kills",
    label = L.text("UI_TGSRR_Tracker_ZombieKills", "Zombie Kills"),
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
    title = L.text("UI_TGSRR_Tracker_Tab_Kills", "Kills"),
    order = 20,
    createView = function(parent, x, y, width, height)
        return KillsView:new(x, y, width, height)
    end,
})

return Tracker.getModule("kills")
