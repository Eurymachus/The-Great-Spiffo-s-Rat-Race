local EventCodec = require "TGSRR/Run/EventCodec"

local Ledger = {}

local ROOT = "TGSRR/Runs"
local MAGIC = 1413960530 -- TGSR
local FILE_FORMAT = 1
local MAX_UTF_BYTES = 60000

local function path(runId, sequence)
    return ROOT .. "/" .. tostring(runId) .. "/events-" .. string.format("%06d", sequence) .. ".bin"
end

local function exists(filename)
    local input = getFileInput(filename)
    if not input then return false end
    input:close()
    return true
end

local function readRecord(runId, sequence)
    local input = getFileInput(path(runId, sequence))
    if not input then return nil, "missing_event_file:" .. tostring(sequence) end
    local ok, result = pcall(function()
        local magic = input:readInt()
        local format = input:readShort()
        local storedSequence = input:readInt()
        local previousHash = input:readUTF()
        local hash = input:readUTF()
        local body = input:readUTF()
        if magic ~= MAGIC then error("invalid_event_magic") end
        if format ~= FILE_FORMAT then error("unsupported_event_file_format") end
        if storedSequence ~= sequence then error("event_sequence_mismatch") end
        return {
            sequence = storedSequence,
            previousHash = tostring(previousHash),
            hash = tostring(hash),
            body = tostring(body),
        }
    end)
    input:close()
    if not ok then return nil, tostring(result) end
    return result
end

local function writeRecord(runId, sequence, record)
    local filename = path(runId, sequence)
    if exists(filename) then return false, "event_file_already_exists:" .. tostring(sequence) end
    if #record.body > MAX_UTF_BYTES then return false, "event_record_too_large" end

    local output = getFileOutput(filename)
    if not output then return false, "unable_to_create_event_file" end
    local ok, err = pcall(function()
        output:writeInt(MAGIC)
        output:writeShort(FILE_FORMAT)
        output:writeInt(sequence)
        output:writeUTF(record.previousHash)
        output:writeUTF(record.hash)
        output:writeUTF(record.body)
        output:flush()
    end)
    output:close()
    if not ok then return false, tostring(err) end

    local written, readError = readRecord(runId, sequence)
    if not written then return false, readError end
    local verified, verifyError = EventCodec.verify(written, record.previousHash)
    if not verified then return false, verifyError end
    if written.hash ~= record.hash or written.body ~= record.body then return false, "event_readback_mismatch" end
    return true
end

function Ledger.initialize(run)
    local sequence = tonumber(run.eventSequence) or 0
    local expectedHash = tostring(run.eventHash or EventCodec.GENESIS_HASH):lower()
    if sequence < 0 or sequence % 1 ~= 0 then return false, "invalid_event_cursor" end
    if #expectedHash ~= 64 or not expectedHash:match("^[0-9a-f]+$") then
        return false, "invalid_event_hash_cursor"
    end

    local previousHash = EventCodec.GENESIS_HASH
    for index = 1, sequence do
        local record, readError = readRecord(run.runId, index)
        if not record then return false, readError end
        local verified, verifyError = EventCodec.verify(record, previousHash)
        if not verified then return false, verifyError .. ":" .. tostring(index) end
        previousHash = record.hash
    end
    if previousHash ~= expectedHash then return false, "event_hash_cursor_mismatch" end
    if exists(path(run.runId, sequence + 1)) then return false, "event_file_ahead_of_save" end
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
    local written, writeError = writeRecord(run.runId, sequence, record)
    if not written then return false, writeError end
    return true, { sequence = sequence, hash = record.hash }
end

Ledger.readRecord = readRecord
Ledger.fileFormat = FILE_FORMAT

return Ledger
