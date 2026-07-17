local Tracker = require "TGSRR/ChallengeTracker"
local OverviewView = require "TGSRR/OverviewTrackerView"
local L = require "TGSRR/Localization"

Tracker.registerModule({
    id = "overview",
    title = L.text("UI_TGSRR_Tracker_Tab_Overview", "Overview"),
    order = 10,
    createView = function(parent, x, y, width, height)
        return OverviewView:new(x, y, width, height)
    end,
})

return Tracker.getModule("overview")
