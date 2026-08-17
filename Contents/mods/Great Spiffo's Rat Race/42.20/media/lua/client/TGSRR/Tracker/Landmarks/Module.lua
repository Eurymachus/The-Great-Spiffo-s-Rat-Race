local Tracker = require "TGSRR/Challenge/TrackerRegistry"
local Deliverables = require "TGSRR/Challenge/Deliverables"
local LandmarkView = require "TGSRR/Tracker/Landmarks/View"
local LocationTracker = require "TGSRR/Run/LocationTracker"
require "TGSRR/Tracker/Landmarks/WorldMap"
local L = require "TGSRR/Core/Localization"

Deliverables.register({
    id = "landmarks",
    label = L.text("UI_TGSRR_Tracker_LandmarksOptional",
        "Landmarks (Optional)"),
    order = 40,
    optional = true,
    getRecord = function()
        local snapshot = LocationTracker.getSnapshot()
        local discovered = 0
        for _, entry in ipairs(snapshot.entries or {}) do
            if entry.visited then discovered = discovered + 1 end
        end
        local total = #(snapshot.entries or {})
        return {
            current = discovered,
            target = total,
            percent = total > 0 and discovered * 100 / total or 0,
            status = total > 0 and discovered == total
                and "complete" or "active",
            detail = L.text("UI_TGSRR_Tracker_LandmarksOptionalDetail",
                "Optional discoveries. They do not affect challenge progress."),
            detailTab = "landmarks",
        }
    end,
})

Tracker.registerModule({
    id = "landmarks",
    title = L.text("UI_TGSRR_Tracker_Tab_Landmarks", "Landmarks"),
    order = 50,
    minimumWidth = LandmarkView.minimumWidth,
    createView = function(parent, x, y, width, height)
        return LandmarkView:new(x, y, width, height)
    end,
})

return Tracker.getModule("landmarks")
