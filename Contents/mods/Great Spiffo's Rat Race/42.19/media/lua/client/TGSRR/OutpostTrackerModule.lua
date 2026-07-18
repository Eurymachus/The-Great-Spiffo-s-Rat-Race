local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local OutpostView = require "TGSRR/OutpostTrackerView"
local Snapshot = require "TGSRR/OutpostTrackerSnapshot"
local L = require "TGSRR/Localization"

Deliverables.register({
    id = "outposts",
    label = L.text("UI_TGSRR_Tracker_Outposts", "Outposts"),
    order = 30,
    getRecord = function(context)
        local snapshot = Snapshot.getAll(context.player)
        return {
            current = snapshot.completed,
            target = #snapshot.rows,
            percent = snapshot.percent,
            status = snapshot.completed == #snapshot.rows and "complete" or "active",
            detail = L.text("UI_TGSRR_Tracker_OutpostsProgress",
                "Mean progress across all registered outposts."),
            detailTab = "outposts",
        }
    end,
})

Tracker.registerModule({
    id = "outposts",
    title = L.text("UI_TGSRR_Tracker_Tab_Outposts", "Outposts"),
    order = 40,
    createView = function(parent, x, y, width, height)
        return OutpostView:new(x, y, width, height)
    end,
})

return Tracker.getModule("outposts")
