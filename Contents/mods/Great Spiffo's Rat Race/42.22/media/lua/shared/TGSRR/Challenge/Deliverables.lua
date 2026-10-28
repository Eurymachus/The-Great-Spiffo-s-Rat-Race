TGSRR = TGSRR or {}

local Deliverables = TGSRR.ChallengeDeliverables or {}
TGSRR.ChallengeDeliverables = Deliverables

Deliverables._providers = Deliverables._providers or {}
Deliverables._ordered = Deliverables._ordered or {}

local function sortProviders()
    table.sort(Deliverables._ordered, function(a, b)
        if a.order == b.order then return a.id < b.id end
        return a.order < b.order
    end)
end

function Deliverables.register(provider)
    if type(provider) ~= "table" then error("TGSRR.ChallengeDeliverables.register: provider is required", 2) end
    if type(provider.id) ~= "string" or provider.id == "" then
        error("TGSRR.ChallengeDeliverables.register: id is required", 2)
    end
    if type(provider.label) ~= "string" or provider.label == "" then
        error("TGSRR.ChallengeDeliverables.register: label is required", 2)
    end
    if type(provider.getRecord) ~= "function" then
        error("TGSRR.ChallengeDeliverables.register: getRecord is required", 2)
    end
    if Deliverables._providers[provider.id] then
        error("TGSRR.ChallengeDeliverables.register: duplicate id " .. provider.id, 2)
    end

    provider.order = tonumber(provider.order) or 100
    Deliverables._providers[provider.id] = provider
    Deliverables._ordered[#Deliverables._ordered + 1] = provider
    sortProviders()
    return provider
end

function Deliverables.getAll(context)
    local records = {}
    for _, provider in ipairs(Deliverables._ordered) do
        local record = provider.getRecord(context or {}) or {}
        record.id = provider.id
        record.label = record.label or provider.label
        record.order = provider.order
        record.optional = provider.optional == true or record.optional == true
        record.available = record.available ~= false
        record.percent = math.max(0, math.min(100, tonumber(record.percent) or 0))
        records[#records + 1] = record
    end
    return records
end

function Deliverables.refreshAll(context)
    for _, provider in ipairs(Deliverables._ordered) do
        if provider.refreshRecord then provider.refreshRecord(context or {}) end
    end
end

return Deliverables
