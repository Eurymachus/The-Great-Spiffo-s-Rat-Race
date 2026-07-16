local Outposts = require "TGSRR/OutpostDefinitions"
require "TGSRR/OutpostRoomActivationCheck"

local Snapshot = {}

function Snapshot.getAll(player)
    local rows = {}
    local activatedRooms = 0
    local totalRooms = 0
    local percentTotal = 0

    for _, outpost in ipairs(Outposts.getAll()) do
        local inspection = Outposts.inspect(outpost, { player = player })
        local activation = inspection.checks and inspection.checks.room_activation or nil
        local current = activation and activation.activatedRooms or 0
        local required = activation and activation.totalRooms or 0
        local progress = required > 0 and current / required or 0

        activatedRooms = activatedRooms + current
        totalRooms = totalRooms + required
        rows[#rows + 1] = {
            id = outpost.id,
            title = outpost.name,
            outpost = outpost,
            activation = activation,
            progress = math.max(0, math.min(1, progress)),
            percent = math.floor(progress * 100 + 0.5),
            complete = required > 0 and current >= required,
            rooms = tostring(current) .. "/" .. tostring(required),
            floors = activation and
                (tostring(activation.activatedFloors) .. "/" .. tostring(activation.totalFloors)) or "-",
            buildings = activation and
                (tostring(activation.resolvedBuildings) .. "/" .. tostring(activation.expectedBuildings)) or "-",
        }
        percentTotal = percentTotal + progress * 100
    end

    local percent = #rows > 0 and percentTotal / #rows or 0
    return {
        rows = rows,
        activatedRooms = activatedRooms,
        totalRooms = totalRooms,
        progress = math.max(0, math.min(1, percent / 100)),
        percent = percent,
    }
end

return Snapshot
