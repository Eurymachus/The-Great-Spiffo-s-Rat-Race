local Tracker = require "TGSRR/Challenge/TrackerRegistry"
local Deliverables = require "TGSRR/Challenge/Deliverables"
local SkillsData = require "TGSRR/Tracker/Skills/Data"
local SkillsView = require "TGSRR/Tracker/Skills/View"
local L = require "TGSRR/Core/Localization"

Deliverables.register({
    id = "skills",
    label = L.text("UI_TGSRR_Tracker_Skills", "Skills"),
    order = 20,
    refreshRecord = function(context)
        SkillsData.refresh(context.player)
    end,
    getRecord = function(context)
        local snapshot = SkillsData.getSnapshot(context.player)
        return {
            available = snapshot.available,
            current = snapshot.mastered,
            target = snapshot.total,
            percent = snapshot.percent,
            status = snapshot.total > 0 and snapshot.mastered == snapshot.total and "complete" or "active",
            detail = L.text("UI_TGSRR_Tracker_SkillsProgress",
                "All registered skills must reach level 10."),
            detailTab = "skills",
        }
    end,
})

Tracker.registerModule({
    id = "skills",
    title = L.text("UI_TGSRR_Tracker_Tab_Skills", "Skills"),
    order = 30,
    createView = function(parent, x, y, width, height)
        return SkillsView:new(x, y, width, height)
    end,
})

return Tracker.getModule("skills")
