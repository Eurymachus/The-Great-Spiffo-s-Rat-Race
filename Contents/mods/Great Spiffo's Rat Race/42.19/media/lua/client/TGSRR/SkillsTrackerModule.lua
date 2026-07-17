local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local PendingView = require "TGSRR/PendingTrackerView"
local L = require "TGSRR/Localization"

local MESSAGE = L.text("UI_TGSRR_Tracker_SkillsPending",
    "Accepted skill set and verification are not implemented.")

Deliverables.register({
    id = "skills",
    label = L.text("UI_TGSRR_Tracker_Skills", "Skills"),
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
    title = L.text("UI_TGSRR_Tracker_Tab_Skills", "Skills"),
    order = 30,
    createView = function(parent, x, y, width, height)
        return PendingView:new(x, y, width, height,
            L.text("UI_TGSRR_Tracker_Skills", "Skills"), MESSAGE)
    end,
})

return Tracker.getModule("skills")
