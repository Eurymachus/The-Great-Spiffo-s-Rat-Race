local Outposts = require "TGSRR/Outposts/Definitions"
local Runtime = require "TGSRR/Outposts/Runtime"
local L = require "TGSRR/Core/Localization"
local Completion = require "TGSRR/Outposts/Completion"
require "TGSRR/Outposts/Checks/RoomActivation"

local Snapshot = {}

function Snapshot.getAll(player)
    local rows = {}
    local activatedRooms = 0
    local totalRooms = 0
    local percentTotal = 0
    local completed = 0

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
        local completion = Completion.calculate(runtimeRecord)
        local progress = completion.progress

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
            percent = math.floor(completion.percent + 0.5),
            complete = completion.complete,
            requirements = tostring(completion.passedRequirements) .. "/" ..
                tostring(completion.totalRequirements),
            rooms = tostring(current) .. "/" .. tostring(required),
            floors = activation and
                (tostring(activation.activatedFloors) .. "/" .. tostring(activation.totalFloors)) or "-",
        }
        if completion.complete then completed = completed + 1 end
        percentTotal = percentTotal + completion.percent
    end

    local percent = #rows > 0 and percentTotal / #rows or 0
    return {
        rows = rows,
        activatedRooms = activatedRooms,
        totalRooms = totalRooms,
        completed = completed,
        progress = math.max(0, math.min(1, percent / 100)),
        percent = percent,
    }
end

return Snapshot
