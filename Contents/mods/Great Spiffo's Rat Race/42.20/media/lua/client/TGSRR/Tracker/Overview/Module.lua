local Tracker = require "TGSRR/Challenge/TrackerRegistry"
local OverviewView = require "TGSRR/Tracker/Overview/View"
local L = require "TGSRR/Core/Localization"

Tracker.registerModule({
    id = "overview",
    title = L.text("UI_TGSRR_Tracker_Tab_Overview", "Overview"),
    order = 10,
    createView = function(parent, x, y, width, height)
        return OverviewView:new(x, y, width, height)
    end,
})

return Tracker.getModule("overview")
