local EventCodec = require "TGSRR/Run/EventCodec"

local Ledger = {}

local ROOT = "TGSRR/Runs"
local SEGMENT_FORMAT = 1
local EVENTS_PER_SEGMENT = 256
local LEGACY_MAGIC = 1413960530 -- TGSR
local LEGACY_FORMAT = 1

local function segmentPath(runId, index)
    return ROOT .. "/" .. tostring(runId) .. "/segments/events-"
        .. string.format("%06d", index) .. ".bin"
end

local function legacyPath(runId, sequence)
    return ROOT .. "/" .. tostring(runId) .. "/events-"
        .. string.format("%06d", sequence) .. ".bin"
end

local function textExists(filename)
    local reader = getFileReader(filename, false)
    if not reader then return false end
    reader:close()
    return true
end

local function binaryExists(filename)
    local input = getFileInput(filename)
    if not input then return false end
    input:close()
    return true
end

local function hexEncode(value)
    return (tostring(value or ""):gsub(".", function(character)
        return string.format("%02x", string.byte(character))
    end))
end

local function hexDecode(value)
    value = tostring(value or "")
    if #value % 2 ~= 0 or value:find("[^0-9a-f]") then return nil, "invalid_record_encoding" end
    return (value:gsub("..", function(pair) return string.char(tonumber(pair, 16)) end))
end

local function recordLine(sequence, record)
    return table.concat({
        "R", tostring(sequence), record.previousHash, record.hash,
        tostring(#record.body), hexEncode(record.body),
    }, "|") .. "\n"
end

local function sealLine(count, sequence, hash)
    return table.concat({ "S", tostring(count), tostring(sequence), hash }, "|") .. "\n"
end

local function readSegment(runId, index, expectedPreviousHash, verifyHashes)
    local reader = getFileReader(segmentPath(runId, index), false)
    if not reader then return nil, "missing_event_segment:" .. tostring(index) end

    local line = reader:readLine()
    local format, storedIndex, startSequence, startHash = nil, nil, nil, nil
    if line then
        format, storedIndex, startSequence, startHash =
            line:match("^H|(%d+)|(%d+)|(%d+)|([0-9a-f]+)$")
    end
    if tonumber(format) ~= SEGMENT_FORMAT or tonumber(storedIndex) ~= index then
        reader:close()
        return nil, "invalid_segment_header:" .. tostring(index)
    end
    if expectedPreviousHash and startHash ~= expectedPreviousHash then
        reader:close()
        return nil, "segment_chain_discontinuity:" .. tostring(index)
    end

    local count = 0
    local previousHash = startHash
    local finalSequence = tonumber(startSequence) - 1
    local sealed = false
    line = reader:readLine()
    while line do
        if sealed then reader:close(); return nil, "frame_after_segment_seal" end
        if line:sub(1, 2) == "R|" then
            local sequenceText, recordPrevious, hash, lengthText, encoded =
                line:match("^R|(%d+)|([0-9a-f]+)|([0-9a-f]+)|(%d+)|([0-9a-f]*)$")
            if not sequenceText then reader:close(); return nil, "truncated_or_invalid_record" end
            local sequence = tonumber(sequenceText)
            if sequence ~= tonumber(startSequence) + count then
                reader:close(); return nil, "event_sequence_mismatch:" .. tostring(sequenceText)
            end
            if recordPrevious ~= previousHash then
                reader:close(); return nil, "chain_discontinuity:" .. tostring(sequence)
            end
            local body, decodeError = hexDecode(encoded)
            if not body then reader:close(); return nil, decodeError end
            if #body ~= tonumber(lengthText) then reader:close(); return nil, "record_length_mismatch" end
            local record = { previousHash = recordPrevious, hash = hash, body = body }
            if verifyHashes ~= false then
                local verified, verifyError = EventCodec.verify(record, previousHash)
                if not verified then reader:close(); return nil, verifyError .. ":" .. tostring(sequence) end
            end
            count = count + 1
            finalSequence = sequence
            previousHash = hash
        elseif line:sub(1, 2) == "S|" then
            local countText, sequenceText, hash = line:match("^S|(%d+)|(%d+)|([0-9a-f]+)$")
            if not countText or tonumber(countText) ~= count or tonumber(sequenceText) ~= finalSequence
                    or hash ~= previousHash then
                reader:close(); return nil, "invalid_segment_seal:" .. tostring(index)
            end
            sealed = true
        else
            reader:close()
            return nil, "invalid_segment_frame:" .. tostring(index)
        end
        line = reader:readLine()
    end
    reader:close()

    if count == 0 then return nil, "empty_event_segment:" .. tostring(index) end
    if count > EVENTS_PER_SEGMENT then return nil, "oversized_event_segment:" .. tostring(index) end
    if count == EVENTS_PER_SEGMENT and not sealed then return nil, "missing_segment_seal:" .. tostring(index) end
    if count < EVENTS_PER_SEGMENT and sealed then return nil, "premature_segment_seal:" .. tostring(index) end
    return {
        index = index,
        count = count,
        startSequence = tonumber(startSequence),
        startHash = startHash,
        finalSequence = finalSequence,
        finalHash = previousHash,
        sealed = sealed,
    }
end

local function readLegacyRecord(runId, sequence)
    local input = getFileInput(legacyPath(runId, sequence))
    if not input then return nil, "missing_legacy_event:" .. tostring(sequence) end
    local ok, result = pcall(function()
        local magic = input:readInt()
        local format = input:readShort()
        local storedSequence = input:readInt()
        local previousHash = tostring(input:readUTF())
        local hash = tostring(input:readUTF())
        local body = tostring(input:readUTF())
        if magic ~= LEGACY_MAGIC or format ~= LEGACY_FORMAT then error("invalid_legacy_event") end
        if storedSequence ~= sequence then error("legacy_event_sequence_mismatch") end
        return { previousHash = previousHash, hash = hash, body = body }
    end)
    input:close()
    if not ok then return nil, tostring(result) end
    return result
end

local function migrateLegacy(run, sequence)
    if sequence == 0 or not binaryExists(legacyPath(run.runId, 1)) then return true end
    -- A legacy record beyond the save's cursor means this save predates data
    -- already written by a later timeline. Never silently absorb that history.
    if binaryExists(legacyPath(run.runId, sequence + 1)) then
        return false, "legacy_event_ahead_of_save"
    end
    local previousHash = EventCodec.GENESIS_HASH
    local writer = nil
    for eventSequence = 1, sequence do
        local record, readError = readLegacyRecord(run.runId, eventSequence)
        if not record then if writer then writer:close() end; return false, readError end
        local verified, verifyError = EventCodec.verify(record, previousHash)
        if not verified then if writer then writer:close() end; return false, verifyError end

        local segmentIndex = math.floor((eventSequence - 1) / EVENTS_PER_SEGMENT) + 1
        local position = ((eventSequence - 1) % EVENTS_PER_SEGMENT) + 1
        if position == 1 then
            local filename = segmentPath(run.runId, segmentIndex)
            if textExists(filename) then return false, "migration_segment_already_exists" end
            writer = getFileWriter(filename, true, false)
            if not writer then return false, "unable_to_create_event_segment" end
            writer:write(table.concat({
                "H", tostring(SEGMENT_FORMAT), tostring(segmentIndex), tostring(eventSequence), previousHash,
            }, "|") .. "\n")
        end
        writer:write(recordLine(eventSequence, record))
        if position == EVENTS_PER_SEGMENT then
            writer:write(sealLine(position, eventSequence, record.hash))
            writer:close()
            writer = nil
        end
        previousHash = record.hash
    end
    if writer then writer:close() end
    return true
end

local function appendRecord(runId, sequence, record)
    local segmentIndex = math.floor((sequence - 1) / EVENTS_PER_SEGMENT) + 1
    local position = ((sequence - 1) % EVENTS_PER_SEGMENT) + 1
    local filename = segmentPath(runId, segmentIndex)
    local writer = nil

    if position == 1 then
        if textExists(filename) then return false, "event_segment_already_exists" end
        writer = getFileWriter(filename, true, false)
        if not writer then return false, "unable_to_create_event_segment" end
        writer:write(table.concat({
            "H", tostring(SEGMENT_FORMAT), tostring(segmentIndex), tostring(sequence), record.previousHash,
        }, "|") .. "\n")
    else
        local segment, readError = readSegment(runId, segmentIndex, nil, false)
        if not segment then return false, readError end
        if segment.sealed or segment.count ~= position - 1 or segment.finalHash ~= record.previousHash then
            return false, "active_segment_cursor_mismatch"
        end
        writer = getFileWriter(filename, false, true)
        if not writer then return false, "unable_to_append_event_segment" end
    end

    writer:write(recordLine(sequence, record))
    if position == EVENTS_PER_SEGMENT then writer:write(sealLine(position, sequence, record.hash)) end
    writer:close()

    local written, verifyError = readSegment(runId, segmentIndex, nil, false)
    if not written then return false, verifyError end
    if written.count ~= position or written.finalSequence ~= sequence or written.finalHash ~= record.hash then
        return false, "event_segment_readback_mismatch"
    end
    return true
end

function Ledger.initialize(run)
    local sequence = tonumber(run.eventSequence) or 0
    local expectedHash = tostring(run.eventHash or EventCodec.GENESIS_HASH):lower()
    if sequence < 0 or sequence % 1 ~= 0 then return false, "invalid_event_cursor" end
    if #expectedHash ~= 64 or not expectedHash:match("^[0-9a-f]+$") then
        return false, "invalid_event_hash_cursor"
    end

    if sequence > 0 and not textExists(segmentPath(run.runId, 1)) then
        local migrated, migrationError = migrateLegacy(run, sequence)
        if not migrated then return false, migrationError end
    end

    local previousHash = EventCodec.GENESIS_HASH
    local consumed = 0
    local segmentCount = math.ceil(sequence / EVENTS_PER_SEGMENT)
    for index = 1, segmentCount do
        local segment, readError = readSegment(run.runId, index, previousHash)
        if not segment then return false, readError end
        consumed = consumed + segment.count
        previousHash = segment.finalHash
    end
    if consumed ~= sequence then return false, "event_segment_ahead_of_save" end
    if previousHash ~= expectedHash then return false, "event_hash_cursor_mismatch" end
    if textExists(segmentPath(run.runId, segmentCount + 1)) then return false, "event_segment_ahead_of_save" end
    return true
end

function Ledger.append(run, event)
    local sequence = (tonumber(run.eventSequence) or 0) + 1
    event.sequence = sequence
    event.runId = run.runId
    event.epoch = tonumber(run.epoch) or 1

    local previousHash = tostring(run.eventHash or EventCodec.GENESIS_HASH):lower()
    local record, encodeError = EventCodec.encode(event, previousHash)
    if not record then return false, encodeError end
    local written, writeError = appendRecord(run.runId, sequence, record)
    if not written then return false, writeError end
    return true, { sequence = sequence, hash = record.hash }
end

Ledger.eventsPerSegment = EVENTS_PER_SEGMENT
Ledger.segmentFormat = SEGMENT_FORMAT

return Ledger
