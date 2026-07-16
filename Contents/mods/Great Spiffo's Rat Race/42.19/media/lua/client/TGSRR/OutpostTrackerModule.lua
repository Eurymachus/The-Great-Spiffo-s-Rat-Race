local Tracker = require "TGSRR/ChallengeTracker"
local Deliverables = require "TGSRR/ChallengeDeliverables"
local OutpostView = require "TGSRR/OutpostTrackerView"
local Snapshot = require "TGSRR/OutpostTrackerSnapshot"

Deliverables.register({
    id = "outposts",
    label = "Outposts",
    order = 30,
    getRecord = function(context)
        local snapshot = Snapshot.getAll(context.player)
        return {
            current = nil,
            target = #snapshot.rows,
            percent = snapshot.percent,
            status = "provisional",
            detail = "Room activation only; completion checks are not implemented.",
            detailTab = "outposts",
        }
    end,
})

Tracker.registerModule({
    id = "outposts",
    title = "Outposts",
    order = 40,
    createView = function(parent, x, y, width, height)
        return OutpostView:new(x, y, width, height)
    end,
})

return Tracker.getModule("outposts")
