local Registry = {}

local definitions = {}
local ordered = {}
local version = 0

local function validPoint(point)
    return type(point) == "table"
        and type(point.id) == "string" and point.id ~= ""
        and tonumber(point.x) ~= nil
        and tonumber(point.y) ~= nil
        and tonumber(point.radius) ~= nil
        and tonumber(point.radius) > 0
end

function Registry.setVersion(value)
    value = math.max(0, math.floor(tonumber(value) or 0))
    if #ordered > 0 and value < 1 then
        error("TGSRR.Locations.setVersion: populated registry requires a version", 2)
    end
    version = value
end

function Registry.getVersion()
    return version
end

function Registry.add(definition)
    if type(definition) ~= "table"
            or type(definition.id) ~= "string" or definition.id == ""
            or type(definition.points) ~= "table" or #definition.points == 0 then
        error("TGSRR.Locations.add: invalid definition", 2)
    end
    if definitions[definition.id] then
        error("TGSRR.Locations.add: duplicate id " .. definition.id, 2)
    end

    local pointIds = {}
    for _, point in ipairs(definition.points) do
        if not validPoint(point) then
            error("TGSRR.Locations.add: invalid point for " .. definition.id, 2)
        end
        if pointIds[point.id] then
            error("TGSRR.Locations.add: duplicate point " .. point.id
                .. " for " .. definition.id, 2)
        end
        pointIds[point.id] = true
        point.x = math.floor(tonumber(point.x))
        point.y = math.floor(tonumber(point.y))
        point.radius = math.floor(tonumber(point.radius))
    end

    definitions[definition.id] = definition
    ordered[#ordered + 1] = definition
    return definition
end

function Registry.get(id)
    return definitions[id]
end

function Registry.getAll()
    return ordered
end

function Registry.findAt(x, y)
    x, y = tonumber(x), tonumber(y)
    if not x or not y then return nil end
    local nearestLocation, nearestPoint, nearestDistance
    for _, location in ipairs(ordered) do
        for _, point in ipairs(location.points) do
            local dx, dy = x - point.x, y - point.y
            local distance = dx * dx + dy * dy
            if distance <= point.radius * point.radius
                    and (not nearestDistance or distance < nearestDistance) then
                nearestLocation, nearestPoint, nearestDistance =
                    location, point, distance
            end
        end
    end
    return nearestLocation, nearestPoint
end

return Registry
