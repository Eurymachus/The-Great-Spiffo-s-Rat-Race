TGSRR = TGSRR or {}

local Outposts = TGSRR.Outposts or {}
TGSRR.Outposts = Outposts

local definitions = Outposts._definitions or {}
local ordered = Outposts._ordered or {}
local checks = Outposts._checks or {}
Outposts._definitions = definitions
Outposts._ordered = ordered
Outposts._checks = checks

local function isNumber(value)
    return type(value) == "number"
end

local function validatePoint(name, point)
    if type(point) ~= "table" then return false, name .. " must be a table" end
    if not isNumber(point.x) or not isNumber(point.y) or not isNumber(point.z) then
        return false, name .. " must contain numeric x, y and z"
    end
    return true
end

local function validateRect(name, rect)
    if type(rect) ~= "table" then return false, name .. " must be a table" end
    if not isNumber(rect.minX) or not isNumber(rect.minY)
            or not isNumber(rect.maxX) or not isNumber(rect.maxY) then
        return false, name .. " must contain numeric minX, minY, maxX and maxY"
    end
    if rect.minX > rect.maxX or rect.minY > rect.maxY then
        return false, name .. " has inverted bounds"
    end
    return true
end

local function clearanceBounds(clearance)
    local minX = clearance.centerX - math.floor(clearance.width / 2)
    local minY = clearance.centerY - math.floor(clearance.height / 2)
    return minX, minY, minX + clearance.width - 1, minY + clearance.height - 1
end

function Outposts.validate(definition)
    if type(definition) ~= "table" then return false, "definition must be a table" end
    if type(definition.id) ~= "string" or definition.id == "" then return false, "id is required" end
    if not definition.id:match("^[a-z0-9_]+$") then
        return false, "id must contain only lowercase letters, numbers and underscores"
    end
    if type(definition.name) ~= "string" or definition.name == "" then return false, "name is required" end

    local valid, reason = validatePoint("anchor", definition.anchor)
    if not valid then return false, reason end
    valid, reason = validateRect("coreZone", definition.coreZone)
    if not valid then return false, reason end

    local clearance = definition.clearance
    if type(clearance) ~= "table" or not isNumber(clearance.centerX)
            or not isNumber(clearance.centerY) or not isNumber(clearance.width)
            or not isNumber(clearance.height) or clearance.width < 1 or clearance.height < 1 then
        return false, "clearance must contain centerX, centerY, width and height"
    end
    if definition.anchor.x < definition.coreZone.minX or definition.anchor.x > definition.coreZone.maxX
            or definition.anchor.y < definition.coreZone.minY or definition.anchor.y > definition.coreZone.maxY then
        return false, "coreZone must contain the anchor"
    end
    local clearanceMinX, clearanceMinY, clearanceMaxX, clearanceMaxY = clearanceBounds(clearance)
    if definition.coreZone.minX < clearanceMinX or definition.coreZone.minY < clearanceMinY
            or definition.coreZone.maxX > clearanceMaxX or definition.coreZone.maxY > clearanceMaxY then
        return false, "coreZone must remain inside clearance"
    end
    if type(definition.buildings) ~= "table" or #definition.buildings == 0 then
        return false, "at least one building is required"
    end
    for index, building in ipairs(definition.buildings) do
        if type(building) ~= "table" or type(building.id) ~= "string" or building.id == "" then
            return false, "buildings[" .. index .. "] requires a string id"
        end
    end
    return true
end

function Outposts.add(definition)
    local valid, reason = Outposts.validate(definition)
    if not valid then error("TGSRR.Outposts.add: " .. tostring(reason), 2) end
    if definitions[definition.id] then error("TGSRR.Outposts.add: duplicate id " .. definition.id, 2) end

    definition.sealingLevel = definition.sealingLevel or 0
    definition.supportRadius = definition.supportRadius or 15
    definition.requireAllRoomsActivated = definition.requireAllRoomsActivated ~= false
    definition.requireZombieClearance = definition.requireZombieClearance ~= false
    definitions[definition.id] = definition
    ordered[#ordered + 1] = definition
    return definition
end

function Outposts.get(id)
    return definitions[id]
end

function Outposts.getClearanceBounds(idOrDefinition)
    local definition = type(idOrDefinition) == "table" and idOrDefinition or definitions[idOrDefinition]
    if not definition then return nil end
    return clearanceBounds(definition.clearance)
end

function Outposts.getAll()
    local result = {}
    for index, definition in ipairs(ordered) do result[index] = definition end
    return result
end

function Outposts.getAt(x, y, z)
    for _, definition in ipairs(ordered) do
        local zone = definition.coreZone
        if (z == nil or z == definition.sealingLevel)
                and x >= zone.minX and x <= zone.maxX
                and y >= zone.minY and y <= zone.maxY then
            return definition
        end
    end
    return nil
end

function Outposts.getAtClearance(x, y)
    for _, definition in ipairs(ordered) do
        local minX, minY, maxX, maxY = clearanceBounds(definition.clearance)
        if x >= minX and x <= maxX and y >= minY and y <= maxY then
            return definition
        end
    end
    return nil
end

function Outposts.getNearest(x, y, maxDistance)
    local nearest, nearestDistance = nil, maxDistance or math.huge
    for _, definition in ipairs(ordered) do
        local dx = x - definition.clearance.centerX
        local dy = y - definition.clearance.centerY
        local distance = math.sqrt(dx * dx + dy * dy)
        if distance <= nearestDistance then
            nearest, nearestDistance = definition, distance
        end
    end
    return nearest, nearestDistance
end

function Outposts.addCheck(id, check, order)
    if type(id) ~= "string" or id == "" then error("TGSRR.Outposts.addCheck: id is required", 2) end
    if type(check) ~= "function" then error("TGSRR.Outposts.addCheck: check must be a function", 2) end
    for _, entry in ipairs(checks) do
        if entry.id == id then error("TGSRR.Outposts.addCheck: duplicate id " .. id, 2) end
    end
    checks[#checks + 1] = { id = id, run = check, order = order or 100 }
    table.sort(checks, function(a, b)
        if a.order == b.order then return a.id < b.id end
        return a.order < b.order
    end)
end

function Outposts.inspect(idOrDefinition, context)
    local definition = type(idOrDefinition) == "table" and idOrDefinition or definitions[idOrDefinition]
    if not definition then return { passed = false, error = "unknown outpost" } end

    local result = { id = definition.id, name = definition.name, passed = true, checks = {} }
    for _, entry in ipairs(checks) do
        local ok, checkResult = pcall(entry.run, definition, context or {})
        if not ok then
            checkResult = { passed = false, error = tostring(checkResult) }
        elseif type(checkResult) == "boolean" then
            checkResult = { passed = checkResult }
        elseif type(checkResult) ~= "table" then
            checkResult = { passed = false, error = "check returned no result" }
        elseif checkResult.passed == nil then
            checkResult.passed = false
        end
        result.checks[entry.id] = checkResult
        if not checkResult.passed then result.passed = false end
    end
    return result
end

return Outposts
