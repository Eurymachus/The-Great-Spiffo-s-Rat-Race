local Store = {}

local MOD_DATA_KEY = "TGSRR_OutpostProgress"
local SCHEMA_VERSION = 5
local PROGRESS_BASELINE_VERSION = 2
local PROGRESS_EPSILON = 0.0001
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
        record = { discovered = false, deliverables = {}, fixtures = {}, progressStage = {} }
        data.outposts[id] = record
    elseif type(record.deliverables) ~= "table" then
        record.deliverables = {}
    end
    if type(record.fixtures) ~= "table" then record.fixtures = {} end
    if type(record.progressStage) ~= "table" then record.progressStage = {} end
    if record.progressStage.baselineVersion ~= PROGRESS_BASELINE_VERSION then
        record.progressStage = {
            baselineVersion = PROGRESS_BASELINE_VERSION,
            baseline = {},
            baselineSealed = false,
            workStarted = false,
        }
    end
    return record
end

local function normalize(result)
    return {
        available = result and result.available ~= false or false,
        passed = result and result.passed == true or false,
        current = result and tonumber(result.current) or 0,
        required = result and tonumber(result.required) or 0,
        state = result and result.state or nil,
        fingerprint = result and result.fingerprint or nil,
        details = result and result.details or nil,
    }
end

local function same(a, b)
    return a and b
        and a.available == b.available
        and a.passed == b.passed
        and a.current == b.current
        and a.required == b.required
        and a.state == b.state
        and a.fingerprint == b.fingerprint
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
    if type(record.fixtures) ~= "table" then record.fixtures = {} end
    if type(record.progressStage) ~= "table" then record.progressStage = {} end
    if record.progressStage.baselineVersion ~= PROGRESS_BASELINE_VERSION then
        record.progressStage = {
            baselineVersion = PROGRESS_BASELINE_VERSION,
            baseline = {},
            baselineSealed = false,
            workStarted = false,
        }
    end
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
        return false, previous, previous
    end

    normalized.observedAt = worldAgeHours()
    record.deliverables[deliverableId] = normalized
    cached[deliverableId] = normalized
    return true, normalized, previous
end

function Store.observeCompletion(id, complete)
    local record = recordFor(id)
    local state = record.completionState
    if type(state) ~= "table" or state.observed ~= true then
        record.completionState = { observed = true, complete = complete == true }
        return nil
    end
    local previous = state.complete == true
    state.complete = complete == true
    if previous == state.complete then return nil end
    return state.complete and "completed" or "regressed"
end

function Store.updateProgressStage(id, fractions, available, sealBaseline)
    local record = recordFor(id)
    local stage = record.progressStage
    if stage.baselineVersion ~= PROGRESS_BASELINE_VERSION then
        stage.baselineVersion = PROGRESS_BASELINE_VERSION
        stage.baseline = {}
        stage.baselineSealed = false
        stage.workStarted = false
        stage.startedAt = nil
    elseif type(stage.baseline) ~= "table" then
        stage.baseline = {}
    end

    local changed = false
    if not stage.baselineSealed then
        for deliverableId, isAvailable in pairs(available or {}) do
            if isAvailable == true then
                local current = math.max(0, math.min(1, tonumber(fractions[deliverableId]) or 0))
                if stage.baseline[deliverableId] ~= current then
                    stage.baseline[deliverableId] = current
                    changed = true
                end
            end
        end
        if sealBaseline == true and not changed then
            stage.baselineSealed = true
            stage.baselineSealedAt = worldAgeHours()
            changed = true
        end
        return changed, false
    end

    for deliverableId, isAvailable in pairs(available or {}) do
        if isAvailable == true then
            local current = math.max(0, math.min(1, tonumber(fractions[deliverableId]) or 0))
            local baseline = stage.baseline[deliverableId]
            if baseline ~= nil and not stage.workStarted and current > baseline + PROGRESS_EPSILON then
                stage.workStarted = true
                stage.startedAt = worldAgeHours()
                changed = true
            end
        end
    end
    return changed, stage.workStarted == true
end

local function fixtureEntries(id, fixtureId)
    local record = recordFor(id)
    local entries = record.fixtures[fixtureId]
    if type(entries) ~= "table" then
        entries = {}
        record.fixtures[fixtureId] = entries
    end
    return entries
end

function Store.addFixture(id, fixtureId, key, details)
    local entries = fixtureEntries(id, fixtureId)
    if entries[key] ~= nil then return false end
    entries[key] = details or true
    return true
end

function Store.removeFixture(id, fixtureId, key)
    local entries = fixtureEntries(id, fixtureId)
    if entries[key] == nil then return false end
    entries[key] = nil
    return true
end

function Store.getFixtureCount(id, fixtureId)
    local entries = fixtureEntries(id, fixtureId)
    local count = 0
    for _ in pairs(entries) do count = count + 1 end
    return count
end

function Store.getFixtureEntries(id, fixtureId)
    return fixtureEntries(id, fixtureId)
end

function Store.getSnapshot()
    return root()
end

return Store
