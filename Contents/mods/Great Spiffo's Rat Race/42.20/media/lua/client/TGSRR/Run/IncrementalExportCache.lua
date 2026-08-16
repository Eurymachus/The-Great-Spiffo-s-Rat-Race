local ExportCodec = require "TGSRR/Run/ExportCodec"
local Hash = require "TGSRR/Run/Hash"

local Cache = {}

local ROOT = "TGSRR/Runs"
local CACHE_VERSION = 3

local function cachePath(runId, firstSequence, count, lastHash)
    return ROOT .. "/" .. tostring(runId) .. "/export-cache-v"
        .. tostring(CACHE_VERSION) .. "/block-"
        .. tostring(firstSequence) .. "-" .. tostring(count) .. "-"
        .. tostring(lastHash) .. ".txt"
end

local function readBlock(path)
    local reader = getFileReader(path, false)
    if not reader then return nil end
    local version = tonumber(reader:readLine())
    local checksum = reader:readLine()
    local encodedChecksum = reader:readLine()
    local value = reader:readLine()
    reader:close()
    if version ~= CACHE_VERSION or type(checksum) ~= "string"
            or #checksum ~= 64 or type(value) ~= "string"
            or type(encodedChecksum) ~= "string"
            or #encodedChecksum ~= 64
            or Hash.sha256(value) ~= encodedChecksum
            or value:sub(-65) ~= "." .. checksum then
        return nil
    end
    return value, checksum
end

local function writeBlock(path, value, checksum)
    local writer = getFileWriter(path, true, false)
    if not writer then return false end
    writer:write(tostring(CACHE_VERSION) .. "\n")
    writer:write(tostring(checksum) .. "\n")
    writer:write(Hash.sha256(value) .. "\n")
    writer:write(tostring(value) .. "\n")
    writer:close()
    return true
end

local function copyRecords(records, firstSequence, lastSequence)
    local result = {}
    for sequence = firstSequence, lastSequence do
        result[#result + 1] = records[sequence]
    end
    return result
end

function Cache.buildBlocks(runId, records, work)
    local blocks = {}
    local reused = 0
    local built = 0
    local blockSize = ExportCodec.eventsPerBlock
    for firstSequence = 1, #records, blockSize do
        local lastSequence = math.min(
            #records, firstSequence + blockSize - 1)
        local count = lastSequence - firstSequence + 1
        local lastHash = records[lastSequence].hash
        local path = cachePath(runId, firstSequence, count, lastHash)
        local value, checksum = readBlock(path)
        local canonicalBytes = 0
        if value then
            reused = reused + 1
        else
            local blockRecords = copyRecords(
                records, firstSequence, lastSequence)
            local stats
            value, stats = ExportCodec.encodeEventBlock(blockRecords, work)
            checksum = stats.checksum
            canonicalBytes = stats.canonicalBytes
            local decoded, decodeError = ExportCodec.decodeEventBlock(
                value, count, work)
            if not decoded then return nil, decodeError end
            for index, record in ipairs(blockRecords) do
                if decoded.bodies[index] ~= record.body then
                    return nil, "export_cache_block_readback_mismatch"
                end
            end
            writeBlock(path, value, checksum)
            built = built + 1
        end
        blocks[#blocks + 1] = {
            count = count,
            firstSequence = firstSequence,
            lastSequence = lastSequence,
            lastHash = lastHash,
            checksum = checksum,
            value = value,
            canonicalBytes = canonicalBytes,
        }
        if work then work("export_blocks", #blocks,
            math.ceil(#records / blockSize)) end
    end
    return blocks, nil, {
        reusedBlockCount = reused,
        builtBlockCount = built,
    }
end

Cache.version = CACHE_VERSION

return Cache
