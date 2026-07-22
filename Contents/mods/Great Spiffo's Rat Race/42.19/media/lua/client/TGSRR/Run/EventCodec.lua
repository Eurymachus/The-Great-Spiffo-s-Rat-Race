local Hash = require "TGSRR/Run/Hash"

local EventCodec = {}

EventCodec.SCHEMA = 1
EventCodec.GENESIS_HASH = string.rep("0", 64)

local function frame(tag, value)
    value = tostring(value or "")
    return tag .. tostring(#value) .. ":" .. value
end

local function canonicalNumber(value)
    if value ~= value or value == math.huge or value == -math.huge then
        error("non_finite_number")
    end
    if value == 0 then return "0" end
    return string.format("%.17g", value)
end

local function tableShape(value)
    local count = 0
    local maximum = 0
    local array = true
    for key, _ in pairs(value) do
        count = count + 1
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then
            array = false
        elseif key > maximum then
            maximum = key
        end
    end
    return array and maximum == count, count
end

local encodeValue

local function encodeTable(value)
    local isArray, count = tableShape(value)
    local parts = {}
    if isArray then
        for index = 1, count do parts[index] = encodeValue(value[index]) end
        return frame("a", table.concat(parts))
    end

    local keys = {}
    for key, _ in pairs(value) do
        if type(key) ~= "string" then error("unsupported_map_key") end
        keys[#keys + 1] = key
    end
    table.sort(keys)
    for _, key in ipairs(keys) do
        parts[#parts + 1] = frame("k", key)
        parts[#parts + 1] = encodeValue(value[key])
    end
    return frame("m", table.concat(parts))
end

encodeValue = function(value)
    local kind = type(value)
    if kind == "nil" then return "z0:" end
    if kind == "boolean" then return frame("b", value and "1" or "0") end
    if kind == "number" then return frame("n", canonicalNumber(value)) end
    if kind == "string" then return frame("s", value) end
    if kind == "table" then return encodeTable(value) end
    error("unsupported_value_type:" .. kind)
end

function EventCodec.canonicalPayload(payload)
    local ok, result = pcall(encodeValue, payload or {})
    if not ok then return nil, tostring(result) end
    return result
end

function EventCodec.canonicalBody(event)
    if type(event) ~= "table" then return nil, "invalid_event" end
    local sequence = tonumber(event.sequence)
    local utc = tonumber(event.utc)
    if not sequence or sequence < 1 or sequence % 1 ~= 0 then return nil, "invalid_sequence" end
    if not utc or utc < 0 or utc % 1 ~= 0 then return nil, "invalid_utc" end
    if not event.runId or tostring(event.runId) == "" then return nil, "missing_run_id" end
    if not event.eventType or tostring(event.eventType) == "" then return nil, "missing_event_type" end

    local payload, payloadError = EventCodec.canonicalPayload(event.payload)
    if not payload then return nil, payloadError end
    local body = table.concat({
        frame("v", EventCodec.SCHEMA),
        frame("r", event.runId),
        frame("e", tonumber(event.epoch) or 1),
        frame("q", sequence),
        frame("t", utc),
        frame("w", canonicalNumber(tonumber(event.worldAgeHours) or 0)),
        frame("y", event.eventType),
        frame("p", payload),
    })
    return body
end

function EventCodec.encode(event, previousHash)
    previousHash = tostring(previousHash or EventCodec.GENESIS_HASH):lower()
    if not previousHash:match("^[0-9a-f]+$") or #previousHash ~= 64 then
        return nil, "invalid_previous_hash"
    end
    local body, bodyError = EventCodec.canonicalBody(event)
    if not body then return nil, bodyError end
    local hash, hashError = Hash.sha256(previousHash .. body)
    if not hash then return nil, hashError end
    return {
        schema = EventCodec.SCHEMA,
        previousHash = previousHash,
        body = body,
        hash = hash,
    }
end

function EventCodec.verify(record, expectedPreviousHash)
    if type(record) ~= "table" then return false, "invalid_record" end
    local previousHash = tostring(record.previousHash or ""):lower()
    if expectedPreviousHash and previousHash ~= tostring(expectedPreviousHash):lower() then
        return false, "chain_discontinuity"
    end
    local actual, err = Hash.sha256(previousHash .. tostring(record.body or ""))
    if not actual then return false, err end
    if actual ~= tostring(record.hash or ""):lower() then return false, "hash_mismatch" end
    return true
end

function EventCodec.selfTest()
    local hashOk, hashError = Hash.selfTest()
    if not hashOk then return false, hashError end

    local first, firstError = EventCodec.encode({
        runId = "rr-test",
        epoch = 1,
        sequence = 1,
        utc = 1234567890,
        worldAgeHours = 12.5,
        eventType = "test",
        payload = { b = "two", a = 1, flags = { true, false } },
    })
    if not first then return false, firstError end
    local second = EventCodec.encode({
        runId = "rr-test",
        epoch = 1,
        sequence = 1,
        utc = 1234567890,
        worldAgeHours = 12.5,
        eventType = "test",
        payload = { flags = { true, false }, a = 1, b = "two" },
    })
    if not second or first.hash ~= second.hash or first.body ~= second.body then
        return false, "canonical_order_self_test_failed"
    end
    return EventCodec.verify(first, EventCodec.GENESIS_HASH)
end

return EventCodec
