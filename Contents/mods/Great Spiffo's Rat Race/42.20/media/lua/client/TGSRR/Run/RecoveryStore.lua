local EventCodec = require "TGSRR/Run/EventCodec"
local Hash = require "TGSRR/Run/Hash"

local RecoveryStore = {}

local ROOT = "TGSRR/Runs"
local FORMAT = 1
local MAX_EPOCHS = 1000

local function metadataPath(runId, epoch)
    return ROOT .. "/" .. tostring(runId) .. "/branches/epoch-"
        .. string.format("%06d", epoch) .. ".meta.txt"
end

function RecoveryStore.segmentPath(runId, epoch, index)
    return ROOT .. "/" .. tostring(runId) .. "/branches/epoch-"
        .. string.format("%06d", epoch) .. "/segments/events-"
        .. string.format("%06d", index) .. ".log"
end

local function textExists(filename)
    local reader = getFileReader(filename, false)
    if not reader then return false end
    reader:close()
    return true
end

local function hexEncode(value)
    return (tostring(value or ""):gsub(".", function(character)
        return string.format("%02x", string.byte(character))
    end))
end

local function hexDecode(value)
    value = tostring(value or "")
    if #value % 2 ~= 0 or value:find("[^0-9a-f]") then
        return nil, "invalid_recovery_metadata_encoding"
    end
    return (value:gsub("..", function(pair)
        return string.char(tonumber(pair, 16))
    end))
end

local function validate(metadata)
    if type(metadata) ~= "table" then
        return false, "invalid_recovery_metadata"
    end
    local integerFields = {
        "epoch", "parentEpoch", "checkpointSequence",
        "supersededEventSequence", "createdUtc",
    }
    for _, field in ipairs(integerFields) do
        local value = tonumber(metadata[field])
        if not value or value < 0 or value % 1 ~= 0 then
            return false, "invalid_recovery_metadata:" .. field
        end
        metadata[field] = value
    end
    if metadata.epoch < 2 or metadata.parentEpoch < 1
            or metadata.parentEpoch >= metadata.epoch then
        return false, "invalid_recovery_epoch_relationship"
    end
    if metadata.supersededEventSequence < metadata.checkpointSequence then
        return false, "invalid_recovery_superseded_cursor"
    end
    for _, field in ipairs({ "checkpointHash", "supersededEventHash" }) do
        local value = tostring(metadata[field] or ""):lower()
        if #value ~= 64 or not value:match("^[0-9a-f]+$") then
            return false, "invalid_recovery_metadata:" .. field
        end
        metadata[field] = value
    end
    if type(metadata.decider) ~= "table"
            or tostring(metadata.decider.type or "") == ""
            or tostring(metadata.decider.id or "") == "" then
        return false, "invalid_recovery_decider"
    end
    return true
end

function RecoveryStore.read(runId, epoch, work)
    epoch = tonumber(epoch)
    if not epoch or epoch < 2 or epoch % 1 ~= 0 then
        return nil, "invalid_recovery_epoch"
    end
    local reader = getFileReader(metadataPath(runId, epoch), false)
    if not reader then return nil, "missing_recovery_metadata:" .. epoch end
    local line = reader:readLine()
    local trailing = reader:readLine()
    reader:close()
    if not line or trailing then return nil, "invalid_recovery_metadata_frame" end
    local formatText, lengthText, encoded, checksum =
        line:match("^R|(%d+)|(%d+)|([0-9a-f]*)|([0-9a-f]+)$")
    if tonumber(formatText) ~= FORMAT then
        return nil, "unsupported_recovery_metadata_format"
    end
    local canonical, decodeError = hexDecode(encoded)
    if not canonical then return nil, decodeError end
    if #canonical ~= tonumber(lengthText) then
        return nil, "recovery_metadata_length_mismatch"
    end
    if Hash.sha256(canonical, work) ~= checksum then
        return nil, "recovery_metadata_checksum_mismatch"
    end
    local metadata, payloadError = EventCodec.decodePayload(canonical)
    if not metadata then return nil, payloadError end
    local valid, validationError = validate(metadata)
    if not valid then return nil, validationError end
    if metadata.epoch ~= epoch then
        return nil, "recovery_metadata_epoch_mismatch"
    end
    metadata.checksum = checksum
    return metadata
end

function RecoveryStore.write(runId, metadata, work)
    local valid, validationError = validate(metadata)
    if not valid then return false, validationError end
    local filename = metadataPath(runId, metadata.epoch)
    if textExists(filename) then
        return false, "recovery_metadata_already_exists"
    end
    local canonical, payloadError = EventCodec.canonicalPayload(metadata)
    if not canonical then return false, payloadError end
    local checksum = Hash.sha256(canonical, work)
    local writer = getFileWriter(filename, true, false)
    if not writer then return false, "unable_to_create_recovery_metadata" end
    writer:write(table.concat({
        "R", tostring(FORMAT), tostring(#canonical),
        hexEncode(canonical), checksum,
    }, "|") .. "\n")
    writer:close()
    local readback, readError =
        RecoveryStore.read(runId, metadata.epoch, work)
    if not readback then return false, readError end
    return true, readback
end

function RecoveryStore.readAll(runId, work)
    local result = {}
    for epoch = 2, MAX_EPOCHS do
        if not textExists(metadataPath(runId, epoch)) then break end
        local metadata, readError = RecoveryStore.read(runId, epoch, work)
        if not metadata then return nil, readError end
        result[#result + 1] = metadata
    end
    return result
end

function RecoveryStore.nextEpoch(runId, work)
    local values, readError = RecoveryStore.readAll(runId, work)
    if not values then return nil, readError end
    return #values + 2
end

function RecoveryStore.findContinuation(runId, parentEpoch,
        checkpointSequence, checkpointHash, supersededEventSequence,
        supersededEventHash, work)
    local values, readError = RecoveryStore.readAll(runId, work)
    if not values then return nil, readError end
    checkpointHash = tostring(checkpointHash or ""):lower()
    supersededEventHash = tostring(supersededEventHash or ""):lower()
    for _, metadata in ipairs(values) do
        if metadata.parentEpoch == tonumber(parentEpoch)
                and metadata.checkpointSequence
                    == tonumber(checkpointSequence)
                and metadata.checkpointHash == checkpointHash
                and metadata.supersededEventSequence
                    == tonumber(supersededEventSequence)
                and metadata.supersededEventHash
                    == supersededEventHash then
            return metadata
        end
    end
    return false
end

RecoveryStore.format = FORMAT

return RecoveryStore
