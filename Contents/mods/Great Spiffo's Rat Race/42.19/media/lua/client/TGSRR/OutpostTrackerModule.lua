local Tracker = require "TGSRR/ChallengeTracker"
local OutpostView = require "TGSRR/OutpostTrackerView"

Tracker.registerModule({
    id = "outposts",
    title = "Outposts",
    order = 10,
    createView = function(parent, x, y, width, height)
        return OutpostView:new(x, y, width, height)
    end,
})

return Tracker.getModule("outposts")
