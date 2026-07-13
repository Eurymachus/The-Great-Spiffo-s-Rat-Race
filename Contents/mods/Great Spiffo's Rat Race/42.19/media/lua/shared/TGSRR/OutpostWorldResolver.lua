local Outposts = require "TGSRR/OutpostDefinitions"

local Resolver = {}

local function includesLevel(levels, level)
    if levels == nil then return true end
    if levels.min ~= nil and levels.max ~= nil then
        return level >= levels.min and level <= levels.max
    end
    for _, allowed in ipairs(levels) do
        if allowed == level then return true end
    end
    return levels[level] == true
end

local function getCandidates(outpost)
    local zone = outpost.coreZone
    local candidates = ArrayList.new()
    getWorld():getMetaGrid():getBuildingsIntersecting(
        zone.minX,
        zone.minY,
        zone.maxX - zone.minX + 1,
        zone.maxY - zone.minY + 1,
        candidates
    )
    return candidates
end

function Resolver.resolveBuildings(outpost)
    local candidates = getCandidates(outpost)
    local byId = {}
    for index = 0, candidates:size() - 1 do
        local definition = candidates:get(index)
        byId[tostring(definition:getIDString())] = definition
    end

    local resolved = {}
    local missing = {}
    for _, registered in ipairs(outpost.buildings) do
        local definition = byId[registered.id]
        if definition then
            resolved[#resolved + 1] = {
                registration = registered,
                definition = definition,
            }
        else
            missing[#missing + 1] = registered.id
        end
    end
    return resolved, missing, candidates
end

function Resolver.resolveRooms(outpost)
    local buildings, missingBuildings = Resolver.resolveBuildings(outpost)
    local rooms = {}
    for _, building in ipairs(buildings) do
        local excludedRoomIds = {}
        for _, roomId in ipairs(building.registration.excludeRoomIds or {}) do
            excludedRoomIds[tostring(roomId)] = true
        end
        local roomDefinitions = building.definition:getRooms()
        for index = 0, roomDefinitions:size() - 1 do
            local room = roomDefinitions:get(index)
            local roomId = tostring(room:getIDString())
            local level = room:getZ()
            local isoRoom = room:getIsoRoom()
            local squares = isoRoom and isoRoom:getSquares() or nil
            local levelIncluded = includesLevel(building.registration.activationLevels, level)
            if not excludedRoomIds[roomId] and levelIncluded then
                rooms[#rooms + 1] = {
                id = roomId,
                name = tostring(room:getName() or "<unnamed>"),
                level = level,
                -- doneSpawn is a public Java field without a Lua-visible getter.
                -- isExplored() is set on the same discovery path immediately
                -- before the room is queued for indoor spawning.
                activated = room:isExplored(),
                explored = room:isExplored(),
                loaded = squares ~= nil and not squares:isEmpty(),
                buildingId = building.registration.id,
                underground = building.registration.underground == true,
                definition = room,
                }
            end
        end
    end
    table.sort(rooms, function(a, b)
        if a.level ~= b.level then return a.level > b.level end
        if a.name ~= b.name then return a.name < b.name end
        return a.id < b.id
    end)
    return rooms, buildings, missingBuildings
end

function Resolver.getOutpostNearPlayer(player, maxDistance)
    if not player then return nil end
    return Outposts.getNearest(player:getX(), player:getY(), maxDistance or 150)
end

return Resolver
