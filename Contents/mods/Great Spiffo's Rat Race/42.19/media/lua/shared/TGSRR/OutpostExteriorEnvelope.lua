local Resolver = require "TGSRR/OutpostWorldResolver"

local Envelope = {}
local cache = {}

local function tileKey(x, y)
    return tostring(x) .. ":" .. tostring(y)
end

local function segmentKey(x, y, north)
    return tileKey(x, y) .. ":" .. (north and "N" or "W")
end

local function windowKind(object)
    if instanceof(object, "IsoWindow") then
        return object:isDestroyed() and "smashed_window" or "window"
    end
    if instanceof(object, "IsoWindowFrame") then return "window_frame" end
    if instanceof(object, "IsoThumpable") and object:isWindow() then return "built_window" end
    return nil
end

local function windowPriority(kind)
    if kind == "window" or kind == "smashed_window" then return 3 end
    if kind == "built_window" then return 2 end
    return 1
end

local function isDoorFrame(object, north)
    if not object then return false end
    if instanceof(object, "IsoThumpable") and object:isDoorFrame() and object:getNorth() == north then return true end
    local properties = object:getProperties()
    return properties and properties:has(north and "DoorWallN" or "DoorWallW") or false
end

local function addSegment(byKey, x, y, z, north)
    local key = segmentKey(x, y, north)
    if byKey[key] then return end
    byKey[key] = { key = key, x = x, y = y, z = z, north = north }
end

local function build(outpost)
    local rooms = Resolver.resolveRooms(outpost)
    local interior = {}
    local interiorCount = 0

    for _, room in ipairs(rooms) do
        if room.level == outpost.sealingLevel then
            local rects = room.definition:getRects()
            for index = 0, rects:size() - 1 do
                local rect = rects:get(index)
                for x = rect:getX(), rect:getX() + rect:getW() - 1 do
                    for y = rect:getY(), rect:getY() + rect:getH() - 1 do
                        local key = tileKey(x, y)
                        if not interior[key] then
                            interior[key] = true
                            interiorCount = interiorCount + 1
                        end
                    end
                end
            end
        end
    end

    if interiorCount == 0 then return nil end

    local byKey = {}
    for key in pairs(interior) do
        local separator = key:find(":", 1, true)
        local x = tonumber(key:sub(1, separator - 1))
        local y = tonumber(key:sub(separator + 1))
        if not interior[tileKey(x, y - 1)] then addSegment(byKey, x, y, outpost.sealingLevel, true) end
        if not interior[tileKey(x - 1, y)] then addSegment(byKey, x, y, outpost.sealingLevel, false) end
        if not interior[tileKey(x, y + 1)] then addSegment(byKey, x, y + 1, outpost.sealingLevel, true) end
        if not interior[tileKey(x + 1, y)] then addSegment(byKey, x + 1, y, outpost.sealingLevel, false) end
    end

    local segments = {}
    for _, segment in pairs(byKey) do segments[#segments + 1] = segment end
    table.sort(segments, function(a, b)
        if a.y ~= b.y then return a.y < b.y end
        if a.x ~= b.x then return a.x < b.x end
        return a.north and not b.north
    end)
    return { segments = segments, interiorCount = interiorCount }
end

function Envelope.get(outpost)
    local envelope = cache[outpost.id]
    if not envelope then
        envelope = build(outpost)
        if envelope then cache[outpost.id] = envelope end
    end
    return envelope
end

function Envelope.invalidate(outpostId)
    cache[outpostId] = nil
end

function Envelope.inspect(outpost, context)
    if context and context.exteriorEnvelopeScan and context.exteriorEnvelopeScan.id == outpost.id then
        return context.exteriorEnvelopeScan
    end

    local envelope = Envelope.get(outpost)
    if not envelope then return { id = outpost.id, available = false, segments = {} } end

    local result = { id = outpost.id, available = true, missingSquares = 0, segments = {} }
    for _, segment in ipairs(envelope.segments) do
        local square = getCell():getGridSquare(segment.x, segment.y, segment.z)
        if not square then
            result.available = false
            result.missingSquares = result.missingSquares + 1
        else
            local window, kind, doorFrame = nil, nil, false
            local objects = square:getObjects()
            for index = 0, objects:size() - 1 do
                local object = objects:get(index)
                local candidateKind = windowKind(object)
                if candidateKind and object:getNorth() == segment.north
                        and (not kind or windowPriority(candidateKind) > windowPriority(kind)) then
                    window, kind = object, candidateKind
                end
                if isDoorFrame(object, segment.north) then doorFrame = true end
            end

            local door = square:getDoor(segment.north)
            local wall = square:getWall(segment.north)
            local solidWall = wall ~= nil and not isDoorFrame(wall, segment.north)
                and windowKind(wall) == nil
            result.segments[#result.segments + 1] = {
                key = segment.key,
                x = segment.x,
                y = segment.y,
                z = segment.z,
                north = segment.north,
                window = window,
                windowKind = kind,
                door = door,
                doorFrame = doorFrame or door ~= nil,
                doorClosed = door ~= nil and not door:IsOpen(),
                solidWall = solidWall,
                sealed = solidWall or window ~= nil or door ~= nil,
            }
        end
    end
    if context then context.exteriorEnvelopeScan = result end
    return result
end

return Envelope
