local Outposts = require "TGSRR/OutpostDefinitions"
local Runtime = require "TGSRR/OutpostRuntimeState"
local L = require "TGSRR/Localization"
require "TGSRR/OutpostRoomActivationCheck"

local Snapshot = {}

function Snapshot.getAll(player)
    local rows = {}
    local activatedRooms = 0
    local totalRooms = 0
    local percentTotal = 0

    for _, outpost in ipairs(Outposts.getAll()) do
        local runtimeRecord = Runtime.getRecord(outpost.id)
        local deliverables = runtimeRecord.deliverables or {}
        local rooms = deliverables.room_activation
        local floors = deliverables.floor_activation
        local activation = rooms and {
            passed = rooms.passed,
            activatedRooms = rooms.current,
            totalRooms = rooms.required,
            activatedFloors = floors and floors.current or 0,
            totalFloors = floors and floors.required or 0,
        } or nil
        local current = rooms and rooms.current or 0
        local required = rooms and rooms.required or 0
        local progress = required > 0 and current / required or 0

        activatedRooms = activatedRooms + current
        totalRooms = totalRooms + required
        rows[#rows + 1] = {
            id = outpost.id,
            title = L.text(outpost.nameKey, outpost.name),
            outpost = outpost,
            activation = activation,
            runtime = runtimeRecord,
            status = Runtime.getStatus(outpost.id),
            progress = math.max(0, math.min(1, progress)),
            percent = math.floor(progress * 100 + 0.5),
            complete = false,
            rooms = tostring(current) .. "/" .. tostring(required),
            floors = activation and
                (tostring(activation.activatedFloors) .. "/" .. tostring(activation.totalFloors)) or "-",
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
