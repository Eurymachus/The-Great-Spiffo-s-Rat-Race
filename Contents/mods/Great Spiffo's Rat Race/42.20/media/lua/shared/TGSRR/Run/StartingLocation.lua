local Outposts = require "TGSRR/Outposts/Definitions"
local Locations = require "TGSRR/Locations/Definitions"

local StartingLocation = {}

local function buildingId(player)
    local square = player and player.getSquare and player:getSquare() or nil
    local building = square and square.getBuilding and square:getBuilding() or nil
    local definition = building and building.getDef and building:getDef() or nil
    return definition and definition.getIDString
        and tostring(definition:getIDString()) or ""
end

local function outpostFor(building, x, y, z)
    for _, outpost in ipairs(Outposts.getAll()) do
        for _, definition in ipairs(outpost.buildings or {}) do
            if building ~= "" and tostring(definition.id) == building then
                return outpost
            end
        end
    end
    return Outposts.getAt(x, y, z)
end

local function landmarkFor(building)
    if building == "" then return nil end
    for _, location in ipairs(Locations.getAll()) do
        for _, id in ipairs(location.buildingIds or {}) do
            if tostring(id) == building then return location end
        end
    end
    return nil
end

function StartingLocation.observe(player, capturedUtc, worldAgeHours, partial)
    local x = math.floor(tonumber(player and player:getX()) or 0)
    local y = math.floor(tonumber(player and player:getY()) or 0)
    local z = math.floor(tonumber(player and player:getZ()) or 0)
    local building = buildingId(player)
    local registered = nil
    local outpost = outpostFor(building, x, y, z)
    if outpost then
        registered = {
            kind = "outpost",
            id = tostring(outpost.id),
            registryVersion = Outposts.getVersion(),
        }
    else
        local landmark = landmarkFor(building)
        if landmark then
            registered = {
                kind = "landmark",
                id = tostring(landmark.id),
                registryVersion = Locations.getVersion(),
            }
        end
    end
    return {
        x = x,
        y = y,
        z = z,
        buildingId = building,
        registeredLocation = registered,
        capturedUtc = math.max(0, math.floor(tonumber(capturedUtc) or 0)),
        worldAgeHours = math.max(0, tonumber(worldAgeHours) or 0),
        partial = partial == true,
    }
end

return StartingLocation
