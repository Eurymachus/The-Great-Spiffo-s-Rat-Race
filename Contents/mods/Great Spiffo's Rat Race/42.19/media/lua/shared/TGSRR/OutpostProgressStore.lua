local Store = {}

local MOD_DATA_KEY = "TGSRR_OutpostProgress"
local SCHEMA_VERSION = 3
local lastWritten = {}

local function worldAgeHours()
    local gameTime = getGameTime()
    return gameTime and gameTime:getWorldAgeHours() or nil
end

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
        data.outposts = {}
        lastWritten = {}
    elseif type(data.outposts) ~= "table" then
        data.outposts = {}
    end
    return data
end

local function recordFor(id)
    local data = root()
    local record = data.outposts[id]
    if type(record) ~= "table" then
        record = { discovered = false, deliverables = {} }
        data.outposts[id] = record
    elseif type(record.deliverables) ~= "table" then
        record.deliverables = {}
    end
    return record
end

local function normalize(result)
    return {
        available = result and result.available ~= false or false,
        passed = result and result.passed == true or false,
        current = result and tonumber(result.current) or 0,
        required = result and tonumber(result.required) or 0,
    }
end

local function same(a, b)
    return a and b
        and a.available == b.available
        and a.passed == b.passed
        and a.current == b.current
        and a.required == b.required
end

local function cacheFor(id)
    local cached = lastWritten[id]
    if not cached then
        cached = {}
        lastWritten[id] = cached
    end
    return cached
end

function Store.get(id)
    local record = root().outposts[id]
    if type(record) ~= "table" then return { discovered = false, deliverables = {} } end
    if type(record.deliverables) ~= "table" then record.deliverables = {} end
    return record
end

function Store.getDeliverable(id, deliverableId)
    return Store.get(id).deliverables[deliverableId]
end

function Store.markDiscovered(id)
    local record = recordFor(id)
    if record.discovered then return false end
    record.discovered = true
    record.discoveredAt = worldAgeHours()
    return true
end

function Store.updateDeliverable(id, deliverableId, result)
    local normalized = normalize(result)
    local record = recordFor(id)
    local cached = cacheFor(id)
    local previous = cached[deliverableId] or record.deliverables[deliverableId]
    if same(previous, normalized) then
        cached[deliverableId] = previous
        return false, previous
    end

    normalized.observedAt = worldAgeHours()
    record.deliverables[deliverableId] = normalized
    cached[deliverableId] = normalized
    return true, normalized
end

function Store.getSnapshot()
    return root()
end

return Store
