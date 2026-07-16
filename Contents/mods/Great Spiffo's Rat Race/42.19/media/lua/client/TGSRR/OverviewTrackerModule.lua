local Tracker = require "TGSRR/ChallengeTracker"
local OverviewView = require "TGSRR/OverviewTrackerView"

Tracker.registerModule({
    id = "overview",
    title = "Overview",
    order = 10,
    createView = function(parent, x, y, width, height)
        return OverviewView:new(x, y, width, height)
    end,
})

return Tracker.getModule("overview")
