local Hash = require "TGSRR/Run/Hash"

local EventCodec = {}

EventCodec.SCHEMA = 2
EventCodec.GENESIS_HASH = string.rep("0", 64)

local function frame(tag, value)
    value = tostring(value or "")
    return tag .. tostring(#value) .. ":" .. value
end

local function readFrame(value, cursor)
    local tag = value:sub(cursor, cursor)
    if tag == "" then return nil, nil, nil, "missing_canonical_frame" end
    local colon = value:find(":", cursor + 1, true)
    if not colon then return nil, nil, nil, "missing_canonical_frame" end
    local lengthText = value:sub(cursor + 1, colon - 1)
    if not lengthText:match("^%d+$") then return nil, nil, nil, "invalid_canonical_frame_length" end
    local first = colon + 1
    local last = first + tonumber(lengthText) - 1
    if last > #value then return nil, nil, nil, "truncated_canonical_frame" end
    return tag, value:sub(first, last), last + 1
end

local function canonicalNumber(value)
    if value ~= value or value == math.huge or value == -math.huge then
        error("non_finite_number")
    end
    if value == 0 then return "0" end
    return string.format("%.17g", value)
end

local function canonicalNumberText(value)
    if value == "0" then return true end
    local mantissa, exponent = value:match("^(-?[1-9]%d*%.?%d*)e([+-]?%d+)$")
    if not mantissa then mantissa = value end
    if exponent and not exponent:match("^[+-]?%d+$") then return false end
    if mantissa:match("^-?[1-9]%d*$") then return true end
    if mantissa:match("^-?[1-9]%d*%.%d+$") then return true end
    return mantissa:match("^-?0%.%d+$") ~= nil
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

local decodeValue

local function decodeTable(tag, value)
    local result = {}
    local cursor = 1
    if tag == "a" then
        while cursor <= #value do
            local decoded, nextCursor, decodeError = decodeValue(value, cursor)
            if decodeError then return nil, decodeError end
            result[#result + 1], cursor = decoded, nextCursor
        end
        return result
    end

    while cursor <= #value do
        local keyTag, key, nextCursor, keyError = readFrame(value, cursor)
        if not keyTag then return nil, keyError end
        if keyTag ~= "k" or key == "" then return nil, "invalid_canonical_map_key" end
        local decoded, valueCursor, decodeError = decodeValue(value, nextCursor)
        if decodeError then return nil, decodeError end
        if result[key] ~= nil then return nil, "duplicate_canonical_map_key" end
        result[key], cursor = decoded, valueCursor
    end
    return result
end

decodeValue = function(value, cursor)
    local tag, framed, nextCursor, readError = readFrame(value, cursor)
    if not tag then return nil, nil, readError end
    if tag == "z" then
        if framed ~= "" then return nil, nil, "invalid_canonical_nil" end
        return nil, nextCursor
    elseif tag == "b" then
        if framed ~= "0" and framed ~= "1" then return nil, nil, "invalid_canonical_boolean" end
        return framed == "1", nextCursor
    elseif tag == "n" then
        local number = tonumber(framed)
        -- Kahlua can parse a correctly formatted 17-digit decimal to the
        -- adjacent double, so formatting the parsed value again is not a
        -- reliable canonical-text check. Validate the encoder's grammar and
        -- finiteness instead.
        if not number or not canonicalNumberText(framed)
                or number ~= number or number == math.huge or number == -math.huge then
            return nil, nil, "invalid_canonical_number"
        end
        return number, nextCursor
    elseif tag == "s" then
        return framed, nextCursor
    elseif tag == "a" or tag == "m" then
        local decoded, decodeError = decodeTable(tag, framed)
        if decodeError then return nil, nil, decodeError end
        return decoded, nextCursor
    end
    return nil, nil, "unsupported_canonical_tag:" .. tostring(tag)
end

function EventCodec.decodePayload(value)
    value = tostring(value or "")
    local decoded, cursor, decodeError = decodeValue(value, 1)
    if decodeError then return nil, decodeError end
    if cursor ~= #value + 1 then return nil, "trailing_canonical_payload_data" end
    if type(decoded) ~= "table" then return nil, "canonical_payload_not_table" end
    return decoded
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

function EventCodec.encode(event, previousHash, work)
    previousHash = tostring(previousHash or EventCodec.GENESIS_HASH):lower()
    if not previousHash:match("^[0-9a-f]+$") or #previousHash ~= 64 then
        return nil, "invalid_previous_hash"
    end
    local body, bodyError = EventCodec.canonicalBody(event)
    if not body then return nil, bodyError end
    local hash, hashError = Hash.sha256(previousHash .. body, work)
    if not hash then return nil, hashError end
    return {
        schema = EventCodec.SCHEMA,
        previousHash = previousHash,
        body = body,
        hash = hash,
    }
end

function EventCodec.verify(record, expectedPreviousHash, work)
    if type(record) ~= "table" then return false, "invalid_record" end
    local previousHash = tostring(record.previousHash or ""):lower()
    if expectedPreviousHash and previousHash ~= tostring(expectedPreviousHash):lower() then
        return false, "chain_discontinuity"
    end
    local actual, err = Hash.sha256(previousHash .. tostring(record.body or ""), work)
    if not actual then return false, err end
    if actual ~= tostring(record.hash or ""):lower() then return false, "hash_mismatch" end
    return true
end

function EventCodec.inspectBody(body)
    body = tostring(body or "")
    local expected = { "v", "r", "e", "q", "t", "w", "y", "p" }
    local values = {}
    local cursor = 1
    for index, expectedTag in ipairs(expected) do
        local tag, value, nextCursor, readError = readFrame(body, cursor)
        if not tag then return nil, readError end
        if tag ~= expectedTag then return nil, "unexpected_canonical_frame:" .. tostring(tag) end
        values[expectedTag], cursor = value, nextCursor
    end
    if cursor ~= #body + 1 then return nil, "trailing_canonical_body_data" end
    if tonumber(values.v) ~= EventCodec.SCHEMA then return nil, "unsupported_event_schema" end
    local sequence = tonumber(values.q)
    local utc = tonumber(values.t)
    local epoch = tonumber(values.e)
    local worldAgeHours = tonumber(values.w)
    if not sequence or sequence < 1 or sequence % 1 ~= 0 then return nil, "invalid_sequence" end
    if not utc or utc < 0 or utc % 1 ~= 0 then return nil, "invalid_utc" end
    if not epoch or epoch < 1 or epoch % 1 ~= 0 then return nil, "invalid_epoch" end
    if not worldAgeHours then return nil, "invalid_world_age" end
    return {
        schema = tonumber(values.v),
        runId = values.r,
        epoch = epoch,
        sequence = sequence,
        utc = utc,
        worldAgeHours = worldAgeHours,
        eventType = values.y,
        canonicalPayload = values.p,
    }
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
    local inspected, inspectError = EventCodec.inspectBody(first.body)
    if not inspected then return false, inspectError end
    if inspected.runId ~= "rr-test" or inspected.sequence ~= 1 or inspected.eventType ~= "test" then
        return false, "canonical_inspection_self_test_failed"
    end
    local payload, payloadError = EventCodec.decodePayload(
        EventCodec.canonicalPayload({ b = "two", a = 1, flags = { true, false } })
    )
    if not payload then return false, payloadError end
    if payload.a ~= 1 or payload.b ~= "two" or payload.flags[1] ~= true
            or payload.flags[2] ~= false then
        return false, "canonical_payload_decode_self_test_failed"
    end
    return EventCodec.verify(first, EventCodec.GENESIS_HASH)
end

return EventCodec
