local Tracker = require "TGSRR/Challenge/TrackerRegistry"
local Deliverables = require "TGSRR/Challenge/Deliverables"
local KillsData = require "TGSRR/Tracker/Kills/Data"
local KillsView = require "TGSRR/Tracker/Kills/View"
local L = require "TGSRR/Core/Localization"

Deliverables.register({
    id = "kills",
    label = L.text("UI_TGSRR_Tracker_ZombieKills", "Kills"),
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
