local Outposts = require "TGSRR/OutpostDefinitions"
local Resolver = require "TGSRR/OutpostWorldResolver"

local function roomActivationCheck(outpost, context)
    local rooms, buildings, missingBuildings = Resolver.resolveRooms(outpost)
    local floorsByLevel = {}
    local inactiveRooms = {}
    local activatedRooms = 0
    local loadedRooms = 0

    for _, room in ipairs(rooms) do
        local floor = floorsByLevel[room.level]
        if not floor then
            floor = { level = room.level, activated = 0, loaded = 0, total = 0, inactiveRooms = {} }
            floorsByLevel[room.level] = floor
        end
        floor.total = floor.total + 1
        if room.activated then
            activatedRooms = activatedRooms + 1
            floor.activated = floor.activated + 1
        else
            inactiveRooms[#inactiveRooms + 1] = room
            floor.inactiveRooms[#floor.inactiveRooms + 1] = room
        end
        if room.loaded then
            loadedRooms = loadedRooms + 1
            floor.loaded = floor.loaded + 1
        end
    end

    local floors = {}
    local activatedFloors = 0
    for _, floor in pairs(floorsByLevel) do
        floor.passed = floor.total > 0 and floor.activated == floor.total
        if floor.passed then activatedFloors = activatedFloors + 1 end
        floors[#floors + 1] = floor
    end
    table.sort(floors, function(a, b) return a.level > b.level end)

    return {
        passed = #missingBuildings == 0 and #rooms > 0 and #inactiveRooms == 0,
        resolvedBuildings = #buildings,
        expectedBuildings = #outpost.buildings,
        missingBuildings = missingBuildings,
        activatedRooms = activatedRooms,
        loadedRooms = loadedRooms,
        totalRooms = #rooms,
        inactiveRooms = inactiveRooms,
        activatedFloors = activatedFloors,
        totalFloors = #floors,
        floors = floors,
    }
end

Outposts.addCheck("room_activation", roomActivationCheck, 10)

return roomActivationCheck
