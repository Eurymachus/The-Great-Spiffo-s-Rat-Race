local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local PendingView = require "TGSRR/PendingTrackerView"

local MESSAGE = "Accepted skill set and verification are not implemented."

Deliverables.register({
    id = "skills",
    label = "Skills",
    order = 20,
    getRecord = function()
        return {
            available = false,
            status = "not_tracked",
            detail = MESSAGE,
            detailTab = "skills",
        }
    end,
})

Tracker.registerModule({
    id = "skills",
    title = "Skills",
    order = 30,
    createView = function(parent, x, y, width, height)
        return PendingView:new(x, y, width, height, "Skills", MESSAGE)
    end,
})

return Tracker.getModule("skills")
