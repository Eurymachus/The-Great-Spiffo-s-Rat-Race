local EventCodec = require "TGSRR/Run/EventCodec"
local Hash = require "TGSRR/Run/Hash"

local ExportCodec = {}

local FORMAT = 4
local LEGACY_FORMAT = 3
local PREFIX = "TGSRR1.BLK1."
local LEGACY_PREFIX = "TGSRR1.LZ1."
local EVENTS_PER_BLOCK = 256
local WINDOW = 4095
local MIN_MATCH = 3
local MAX_MATCH = 18
local MAX_CANDIDATES = 64
local MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024
local BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

local function phaseWork(work, phase)
    if not work then return nil end
    return function(_, current, total)
        work(phase, current, total)
    end
end

local function frame(value)
    value = tostring(value or "")
    return tostring(#value) .. ":" .. value
end

local function readFrame(value, cursor)
    local colon = value:find(":", cursor, true)
    if not colon then return nil, nil, "missing_export_frame" end
    local lengthText = value:sub(cursor, colon - 1)
    if not lengthText:match("^%d+$") then return nil, nil, "invalid_export_frame_length" end
    local length = tonumber(lengthText)
    local first = colon + 1
    local last = first + length - 1
    if last > #value then return nil, nil, "truncated_export_frame" end
    return value:sub(first, last), last + 1
end

local function base64Encode(value, work)
    local result = {}
    for index = 1, #value, 3 do
        local a = string.byte(value, index) or 0
        local b = string.byte(value, index + 1)
        local c = string.byte(value, index + 2)
        local packed = a * 65536 + (b or 0) * 256 + (c or 0)
        result[#result + 1] = BASE64:sub(math.floor(packed / 262144) % 64 + 1, math.floor(packed / 262144) % 64 + 1)
        result[#result + 1] = BASE64:sub(math.floor(packed / 4096) % 64 + 1, math.floor(packed / 4096) % 64 + 1)
        if b then result[#result + 1] = BASE64:sub(math.floor(packed / 64) % 64 + 1, math.floor(packed / 64) % 64 + 1) end
        if c then result[#result + 1] = BASE64:sub(packed % 64 + 1, packed % 64 + 1) end
        if work and index % 768 == 1 then work("encode", index, #value) end
    end
    return table.concat(result)
end

local function base64Decode(value, work)
    value = tostring(value or "")
    if value:find("[^A-Za-z0-9_-]") or #value % 4 == 1 then return nil, "invalid_export_base64" end
    local lookup = {}
    for index = 1, #BASE64 do lookup[BASE64:sub(index, index)] = index - 1 end
    local result = {}
    for index = 1, #value, 4 do
        local remaining = math.min(4, #value - index + 1)
        local a = lookup[value:sub(index, index)]
        local b = lookup[value:sub(index + 1, index + 1)]
        local c = remaining >= 3 and lookup[value:sub(index + 2, index + 2)] or 0
        local d = remaining >= 4 and lookup[value:sub(index + 3, index + 3)] or 0
        if a == nil or b == nil or c == nil or d == nil then return nil, "invalid_export_base64" end
        local packed = a * 262144 + b * 4096 + c * 64 + d
        result[#result + 1] = string.char(math.floor(packed / 65536) % 256)
        if remaining >= 3 then result[#result + 1] = string.char(math.floor(packed / 256) % 256) end
        if remaining >= 4 then result[#result + 1] = string.char(packed % 256) end
        if work and index % 1024 == 1 then work("verify", index, #value) end
    end
    return table.concat(result)
end

local function addPosition(positions, value, index)
    if index + MIN_MATCH - 1 > #value then return end
    local key = value:sub(index, index + MIN_MATCH - 1)
    local values = positions[key]
    if not values then values = {}; positions[key] = values end
    values[#values + 1] = index
end

local function bestMatch(value, index, positions)
    if index + MIN_MATCH - 1 > #value then return 0, 0 end
    local candidates = positions[value:sub(index, index + MIN_MATCH - 1)]
    if not candidates then return 0, 0 end
    local bestOffset, bestLength = 0, 0
    local checked = 0
    for candidateIndex = #candidates, 1, -1 do
        local candidate = candidates[candidateIndex]
        local offset = index - candidate
        if offset > WINDOW then break end
        checked = checked + 1
        local length = MIN_MATCH
        while length < MAX_MATCH and index + length <= #value
                and value:byte(candidate + (length % offset)) == value:byte(index + length) do
            length = length + 1
        end
        if length > bestLength then
            bestOffset, bestLength = offset, length
            if length == MAX_MATCH then break end
        end
        if checked >= MAX_CANDIDATES then break end
    end
    return bestOffset, bestLength
end

local function compress(value, work)
    local output = {}
    local positions = {}
    local index = 1
    while index <= #value do
        local flagIndex = #output + 1
        output[flagIndex] = ""
        local flags = 0
        for bit = 0, 7 do
            if index > #value then break end
            local offset, length = bestMatch(value, index, positions)
            local consumed
            if length >= MIN_MATCH then
                output[#output + 1] = string.char(math.floor(offset / 16))
                output[#output + 1] = string.char((offset % 16) * 16 + (length - MIN_MATCH))
                consumed = length
            else
                flags = flags + (2 ^ bit)
                output[#output + 1] = value:sub(index, index)
                consumed = 1
            end
            for position = index, index + consumed - 1 do addPosition(positions, value, position) end
            index = index + consumed
        end
        output[flagIndex] = string.char(flags)
        if work then work("compress", index, #value) end
    end
    return table.concat(output)
end

local function decompress(value, work)
    local output = {}
    local length = 0
    local index = 1
    while index <= #value do
        local flags = value:byte(index)
        if not flags then return nil, "truncated_export_compression" end
        index = index + 1
        for bit = 0, 7 do
            if index > #value then break end
            if math.floor(flags / (2 ^ bit)) % 2 == 1 then
                length = length + 1
                if length > MAX_DECOMPRESSED_BYTES then return nil, "export_too_large" end
                output[length] = value:sub(index, index)
                index = index + 1
            else
                local high, low = value:byte(index), value:byte(index + 1)
                if not high or not low then return nil, "truncated_export_match" end
                index = index + 2
                local offset = high * 16 + math.floor(low / 16)
                local matchLength = (low % 16) + MIN_MATCH
                if offset < 1 or offset > length then return nil, "invalid_export_match" end
                for _ = 1, matchLength do
                    length = length + 1
                    if length > MAX_DECOMPRESSED_BYTES then return nil, "export_too_large" end
                    output[length] = output[length - offset]
                end
            end
        end
        if work and index % 256 < 16 then work("verify", index, #value) end
    end
    return table.concat(output)
end

local function encodeCompressedCanonical(canonical, work)
    local checksum = Hash.sha256(canonical,
        phaseWork(work, "create_checksum"))
    return base64Encode(compress(canonical, work), work), checksum
end

local function decodeCompressedCanonical(payload, checksum, work)
    local compressed, base64Error = base64Decode(
        payload, phaseWork(work, "decode"))
    if not compressed then return nil, base64Error end
    local canonical, compressionError = decompress(
        compressed, phaseWork(work, "decompress"))
    if not canonical then return nil, compressionError end
    if Hash.sha256(canonical, phaseWork(work, "verify_checksum"))
            ~= checksum then
        return nil, "export_checksum_mismatch"
    end
    return canonical
end

local function canonicalBodies(records)
    local bodies = {}
    for _, record in ipairs(records or {}) do
        bodies[#bodies + 1] = frame(record.body)
    end
    return table.concat(bodies)
end

local function parseBodies(canonical, count)
    local bodies = {}
    local cursor = 1
    for _ = 1, count do
        local body, nextCursor, readError = readFrame(canonical, cursor)
        if not body then return nil, readError end
        bodies[#bodies + 1], cursor = body, nextCursor
    end
    if cursor ~= #canonical + 1 then return nil, "export_event_count_mismatch" end
    return bodies
end

function ExportCodec.encodeEventBlock(records, work)
    local canonical = canonicalBodies(records)
    local payload, checksum = encodeCompressedCanonical(canonical, work)
    return payload .. "." .. checksum, {
        count = #(records or {}),
        checksum = checksum,
        canonicalBytes = #canonical,
        encodedCharacters = #payload + #checksum + 1,
    }
end

function ExportCodec.decodeEventBlock(value, count, work)
    local payload, checksum = tostring(value or ""):match(
        "^([A-Za-z0-9_-]+)%.([0-9a-f]+)$")
    if not payload or #checksum ~= 64 then
        return nil, "invalid_export_event_block"
    end
    local canonical, decodeError = decodeCompressedCanonical(
        payload, checksum, work)
    if not canonical then return nil, decodeError end
    local bodies, bodiesError = parseBodies(canonical, count)
    if not bodies then return nil, bodiesError end
    return {
        checksum = checksum,
        bodies = bodies,
        canonicalBytes = #canonical,
    }
end

local function canonicalEnvelope(runId, generatedUtc, records, eventHash, projection)
    local bodies = {}
    for _, record in ipairs(records) do bodies[#bodies + 1] = frame(record.body) end
    projection = projection or {}
    return table.concat({
        frame(FORMAT),
        frame(runId),
        frame(generatedUtc),
        frame(#records),
        frame(eventHash),
        frame(EventCodec.canonicalPayload(projection)),
        frame(table.concat(bodies)),
    })
end

local function parseEnvelope(value)
    local cursor = 1
    local fields = {}
    local formatText, nextCursor, formatError = readFrame(value, cursor)
    if not formatText then return nil, formatError end
    local format = tonumber(formatText)
    if format ~= LEGACY_FORMAT then return nil, "unsupported_export_format" end
    fields[1], cursor = formatText, nextCursor
    local fieldCount = 7
    for index = 2, fieldCount do
        local field, nextCursor, readError = readFrame(value, cursor)
        if not field then return nil, readError end
        fields[index], cursor = field, nextCursor
    end
    if cursor ~= #value + 1 then return nil, "trailing_export_data" end
    if not tonumber(fields[3]) or tonumber(fields[3]) < 0 or tonumber(fields[3]) % 1 ~= 0 then
        return nil, "invalid_export_timestamp"
    end
    if #fields[5] ~= 64 or not fields[5]:match("^[0-9a-f]+$") then
        return nil, "invalid_export_ledger_head"
    end
    local count = tonumber(fields[4])
    if not count or count < 0 or count % 1 ~= 0 then return nil, "invalid_export_event_count" end
    local currentKills = nil
    local projection = {}
    local bodiesField = 7
    local projectionError
    projection, projectionError = EventCodec.decodePayload(fields[6])
    if not projection then return nil, projectionError end
    currentKills = tonumber(projection.currentKills)
    if not currentKills or currentKills < 0 or currentKills % 1 ~= 0 then
        return nil, "invalid_export_current_kills"
    end
    local bodies = {}
    local bodyCursor = 1
    for _ = 1, count do
        local body, nextCursor, readError = readFrame(fields[bodiesField], bodyCursor)
        if not body then return nil, readError end
        bodies[#bodies + 1], bodyCursor = body, nextCursor
    end
    if bodyCursor ~= #fields[bodiesField] + 1 then return nil, "export_event_count_mismatch" end
    return {
        format = format,
        runId = fields[2],
        generatedUtc = tonumber(fields[3]),
        eventSequence = count,
        eventHash = fields[5],
        currentKills = currentKills,
        projection = projection,
        bodies = bodies,
    }
end

function ExportCodec.encode(runId, generatedUtc, records, eventHash,
        projection, work, options)
    options = options or {}
    local blocks = options.blocks or {}
    local descriptors = {}
    local encodedBlocks = {}
    local canonicalBytes = 0
    for index, block in ipairs(blocks) do
        descriptors[index] = {
            count = block.count,
            firstSequence = block.firstSequence,
            lastSequence = block.lastSequence,
            lastHash = block.lastHash,
            checksum = block.checksum,
        }
        encodedBlocks[index] = block.value
        canonicalBytes = canonicalBytes + (tonumber(block.canonicalBytes) or 0)
    end
    if #blocks == 0 and #(records or {}) > 0 then
        for first = 1, #records, EVENTS_PER_BLOCK do
            local blockRecords = {}
            local last = math.min(#records, first + EVENTS_PER_BLOCK - 1)
            for sequence = first, last do
                blockRecords[#blockRecords + 1] = records[sequence]
            end
            local value, stats = ExportCodec.encodeEventBlock(blockRecords, work)
            local descriptor = {
                count = #blockRecords,
                firstSequence = first,
                lastSequence = last,
                lastHash = records[last].hash,
                checksum = stats.checksum,
            }
            descriptors[#descriptors + 1] = descriptor
            encodedBlocks[#encodedBlocks + 1] = value
            canonicalBytes = canonicalBytes + stats.canonicalBytes
        end
    end
    local manifest = {
        format = FORMAT,
        runId = runId,
        generatedUtc = generatedUtc,
        eventSequence = #(records or {}),
        eventHash = eventHash,
        projection = projection or {},
        eventBlocks = descriptors,
    }
    local manifestCanonical = EventCodec.canonicalPayload(manifest)
    local manifestPayload, manifestChecksum =
        encodeCompressedCanonical(manifestCanonical, work)
    local parts = { PREFIX .. manifestPayload, manifestChecksum }
    for _, block in ipairs(encodedBlocks) do parts[#parts + 1] = block end
    local encoded = table.concat(parts, ".")
    return encoded, {
        canonicalBytes = canonicalBytes + #manifestCanonical,
        encodedCharacters = #encoded,
        checksum = manifestChecksum,
        blockCount = #descriptors,
        reusedBlockCount = tonumber(options.reusedBlockCount) or 0,
        builtBlockCount = #descriptors - (tonumber(options.reusedBlockCount) or 0),
    }
end

function ExportCodec.decodeManifest(value, work)
    value = tostring(value or "")
    if value:sub(1, #LEGACY_PREFIX) == LEGACY_PREFIX then
        local payload, checksum = value:match(
            "^TGSRR1%.LZ1%.([A-Za-z0-9_-]+)%.([0-9a-f]+)$")
        if not payload or #checksum ~= 64 then return nil, "invalid_export_envelope" end
        local canonical, decodeError = decodeCompressedCanonical(
            payload, checksum, work)
        if not canonical then return nil, decodeError end
        local decoded, parseError = parseEnvelope(canonical)
        if not decoded then return nil, parseError end
        decoded.checksum = checksum
        decoded.legacy = true
        return decoded
    end
    local parts = {}
    for part in value:gmatch("[^.]+") do parts[#parts + 1] = part end
    if #parts < 4 or parts[1] ~= "TGSRR1" or parts[2] ~= "BLK1"
            or #parts % 2 ~= 0 then
        return nil, "invalid_export_envelope"
    end
    local manifestCanonical, manifestError = decodeCompressedCanonical(
        parts[3], parts[4], work)
    if not manifestCanonical then return nil, manifestError end
    local manifest, payloadError = EventCodec.decodePayload(manifestCanonical)
    if not manifest then return nil, payloadError end
    if manifest.format ~= FORMAT or type(manifest.eventBlocks) ~= "table" then
        return nil, "unsupported_export_format"
    end
    if #parts ~= 4 + #manifest.eventBlocks * 2 then
        return nil, "export_block_count_mismatch"
    end
    local decoded = {
        format = FORMAT,
        runId = manifest.runId,
        generatedUtc = manifest.generatedUtc,
        eventSequence = manifest.eventSequence,
        eventHash = manifest.eventHash,
        projection = manifest.projection,
        currentKills = manifest.projection and manifest.projection.currentKills,
        bodies = {},
        checksum = parts[4],
        eventBlocks = manifest.eventBlocks,
        eventBlockValues = {},
    }
    local expectedFirst = 1
    for index, descriptor in ipairs(manifest.eventBlocks) do
        if descriptor.firstSequence ~= expectedFirst
                or descriptor.lastSequence ~= expectedFirst + descriptor.count - 1
                or descriptor.checksum ~= parts[4 + index * 2] then
            return nil, "invalid_export_event_block_descriptor"
        end
        decoded.eventBlockValues[index] = parts[3 + index * 2] .. "."
            .. parts[4 + index * 2]
        expectedFirst = descriptor.lastSequence + 1
    end
    if expectedFirst - 1 ~= decoded.eventSequence then
        return nil, "export_event_count_mismatch"
    end
    return decoded
end

function ExportCodec.decode(value, work, options)
    options = options or {}
    local decoded, manifestError = ExportCodec.decodeManifest(value, work)
    if not decoded then return nil, manifestError end
    if decoded.legacy then return decoded end
    for index, descriptor in ipairs(decoded.eventBlocks) do
        local blockValue = decoded.eventBlockValues[index]
        local block, blockError = ExportCodec.decodeEventBlock(
            blockValue, descriptor.count, work)
        if not block then return nil, blockError end
        for _, body in ipairs(block.bodies) do
            decoded.bodies[#decoded.bodies + 1] = body
        end
    end
    if #decoded.bodies ~= decoded.eventSequence then
        return nil, "export_event_count_mismatch"
    end

    if options.verifyLedger ~= false then
        local previousHash = EventCodec.GENESIS_HASH
        for sequence, body in ipairs(decoded.bodies) do
            local event, inspectError = EventCodec.inspectBody(body)
            if not event then return nil, inspectError end
            if event.runId ~= decoded.runId then return nil, "export_run_id_mismatch" end
            if event.sequence ~= sequence then return nil, "export_event_sequence_mismatch" end
            local hash = Hash.sha256(previousHash .. body,
                phaseWork(work, "verify_history"))
            previousHash = hash
            if sequence == decoded.eventSequence and hash ~= decoded.eventHash then
                return nil, "export_ledger_head_mismatch"
            end
        end
        if decoded.eventSequence == 0 and decoded.eventHash ~= EventCodec.GENESIS_HASH then
            return nil, "export_ledger_head_mismatch"
        end
    end
    return decoded
end

function ExportCodec.selfTest(work)
    local previousHash = EventCodec.GENESIS_HASH
    local records = {}
    for sequence = 1, 2 do
        local record, encodeError = EventCodec.encode({
            runId = "rr-export-test",
            epoch = 1,
            sequence = sequence,
            utc = 1234567890 + sequence,
            worldAgeHours = sequence,
            eventType = "export.test",
            payload = { repeated = "alpha alpha alpha", sequence = sequence },
        }, previousHash)
        if not record then return false, encodeError end
        records[#records + 1] = record
        previousHash = record.hash
    end
    local encoded = ExportCodec.encode(
        "rr-export-test", 1234567890, records, previousHash, {
            schema = 1,
            challenge = {
                id = "TGSRR_CDDA",
                gameMode = "The Great Spiffo's Rat Race - CDDA",
            },
            currentKills = 42,
            weight = {
                unit = "kilogram",
                currentKilograms = 78.25,
            },
            character = {
                starting = { professionId = "carpenter" },
                current = { professionId = "carpenter" },
                selectedStartingTraits = { "base:Brave", "base:Strong" },
                currentEffectiveTraits = { "base:Brave" },
            },
            skills = {
                { id = "Fitness", categoryId = "Passive", level = 7, xp = 12345.5 },
                { id = "Sprinting", categoryId = "Agility", level = 4, xp = 678.25 },
            },
            outposts = {
                {
                    id = "echo_creek_church",
                    discovered = true,
                    discoveredWorldAgeHours = 12.5,
                    stage = "in_progress",
                    complete = false,
                    progress = 0.42,
                    passedRequirements = 5,
                    totalRequirements = 14,
                    workStartedWorldAgeHours = 15,
                    deliverables = {
                        {
                            id = "food",
                            available = true,
                            passed = false,
                            current = 20,
                            required = 40,
                            progress = 0.5,
                            observedWorldAgeHours = 16,
                        },
                    },
                },
            },
            challengeProgress = {
                rulesVersion = 1,
                categories = {
                    kills = {
                        available = true,
                        current = 42,
                        target = 1000000,
                        progress = 0.000042,
                        status = "active",
                    },
                    skills = {
                        available = true,
                        current = 0,
                        target = 2,
                        progress = 0.55,
                        status = "active",
                    },
                    outposts = {
                        available = true,
                        current = 0,
                        target = 1,
                        progress = 0.42,
                        status = "active",
                    },
                },
            },
            activeMods = {
                { modId = "TGSRR", workshopId = "1234567890" },
                { modId = "example.local", workshopId = "" },
            },
            activeDay = {
                dayIndex = 4,
                baselinePartial = false,
                startedUtc = 1234560000,
                startedWorldAgeHours = 72,
                observedUtc = 1234567890,
                observedWorldAgeHours = 79.5,
                elapsedWorldHours = 7.5,
                killDelta = 87,
                weightDeltaKilograms = -0.75,
                xpDeltas = { Fitness = 45.25, Sprinting = 12 },
                weaponKillDeltas = { ["Base.Axe"] = 3, __VEHICLE__ = 2 },
                weaponKillsPartial = false,
                fireDeathDelta = 6,
                fireDeathsPartial = false,
                distanceDeltaMeters = 1250.5,
                distancePartial = false,
                brokenWeaponDeltas = {
                    ["Base.Axe"] = 1,
                    ["Base.HuntingKnife"] = 2,
                },
                brokenWeaponsPartial = false,
            },
            weaponKills = {
                partial = false,
                baselineTotal = 0,
                sources = {
                    { id = "Base.Axe", kills = 12 },
                    { id = "__VEHICLE__", kills = 4 },
                },
            },
            fireDeaths = { count = 19, partial = false },
            zombieKillTypes = {
                standing = 10,
                onfront = 11,
                onback = 12,
                fenceAssist = 8,
                windowAssist = 1,
                partial = false,
            },
            milestones = {
                schema = 1,
                partial = false,
                outpostCompletions = {
                    {
                        outpostId = "echo_creek_church",
                        completionOrder = 1,
                        sequence = 20,
                        utc = 1234567890,
                        worldAgeHours = 96,
                        elapsedDays = 4,
                    },
                },
                killMilestones = {
                    {
                        threshold = 1000,
                        killTotal = 1002,
                        characterId = "player",
                        sequence = 18,
                        utc = 1234567800,
                        worldAgeHours = 72,
                        elapsedDays = 3,
                    },
                },
                skillMilestones = {
                    {
                        skillId = "Fitness",
                        categoryId = "Passive",
                        level = 10,
                        completionOrder = 1,
                        sequence = 19,
                        utc = 1234567850,
                        worldAgeHours = 84,
                        elapsedDays = 3.5,
                    },
                },
                outpostDeliverableMilestones = {},
            },
            distance = {
                unit = "meter",
                travelledMeters = 12345.75,
                rejectedSamples = 2,
                partial = false,
            },
            nimbleStance = {
                unit = "millisecond",
                movementMilliseconds = 98765,
                partial = false,
            },
            activeGameplay = {
                unit = "millisecond",
                milliseconds = 456789,
                partial = false,
            },
            brokenWeapons = {
                total = 3,
                partial = false,
                weapons = {
                    { id = "Base.Axe", breaks = 1 },
                    { id = "Base.HuntingKnife", breaks = 2 },
                },
            },
        }, work
    )
    local decoded, decodeError = ExportCodec.decode(encoded, work)
    if not decoded then return false, decodeError end
    if decoded.runId ~= "rr-export-test" or decoded.eventSequence ~= #records
            or decoded.currentKills ~= 42
            or decoded.projection.challenge.id ~= "TGSRR_CDDA"
            or decoded.projection.challenge.gameMode ~=
                "The Great Spiffo's Rat Race - CDDA"
            or decoded.projection.character.selectedStartingTraits[2] ~= "base:Strong"
            or decoded.projection.character.starting.professionId ~= "carpenter"
            or decoded.projection.character.current.professionId ~= "carpenter"
            or decoded.projection.skills[2].id ~= "Sprinting"
            or decoded.projection.skills[2].level ~= 4
            or decoded.projection.skills[2].xp ~= 678.25
            or decoded.projection.outposts[1].id ~= "echo_creek_church"
            or decoded.projection.outposts[1].deliverables[1].progress ~= 0.5
            or decoded.projection.challengeProgress.rulesVersion ~= 1
            or decoded.projection.challengeProgress.categories.skills.progress ~= 0.55
            or decoded.projection.activeMods[1].modId ~= "TGSRR"
            or decoded.projection.activeMods[2].workshopId ~= ""
            or decoded.projection.weight.unit ~= "kilogram"
            or decoded.projection.weight.currentKilograms ~= 78.25
            or decoded.projection.milestones.outpostCompletions[1].completionOrder ~= 1
            or decoded.projection.milestones.killMilestones[1].threshold ~= 1000
            or decoded.projection.milestones.skillMilestones[1].skillId ~= "Fitness"
            or decoded.projection.milestones.skillMilestones[1].level ~= 10
            or decoded.projection.milestones.skillMilestones[1].completionOrder ~= 1
            or decoded.projection.distance.travelledMeters ~= 12345.75
            or decoded.projection.nimbleStance.unit ~= "millisecond"
            or decoded.projection.nimbleStance.movementMilliseconds ~= 98765
            or decoded.projection.activeGameplay.unit ~= "millisecond"
            or decoded.projection.activeGameplay.milliseconds ~= 456789
            or decoded.projection.activeDay.distanceDeltaMeters ~= 1250.5
            or decoded.projection.activeDay.weightDeltaKilograms ~= -0.75
            or decoded.projection.brokenWeapons.total ~= 3
            or decoded.projection.brokenWeapons.weapons[2].breaks ~= 2
            or decoded.projection.activeDay.brokenWeaponDeltas["Base.Axe"] ~= 1
            or decoded.projection.activeDay.dayIndex ~= 4
            or decoded.projection.activeDay.xpDeltas.Fitness ~= 45.25
            or decoded.projection.activeDay.weaponKillDeltas.__VEHICLE__ ~= 2
            or decoded.projection.weaponKills.sources[1].id ~= "Base.Axe"
            or decoded.projection.weaponKills.sources[1].kills ~= 12
            or decoded.projection.fireDeaths.count ~= 19
            or decoded.projection.zombieKillTypes.standing ~= 10
            or decoded.projection.zombieKillTypes.onfront ~= 11
            or decoded.projection.zombieKillTypes.onback ~= 12
            or decoded.projection.zombieKillTypes.fenceAssist ~= 8
            or decoded.projection.zombieKillTypes.windowAssist ~= 1
            or decoded.projection.activeDay.fireDeathDelta ~= 6
            or decoded.eventHash ~= previousHash or decoded.bodies[2] ~= records[2].body then
        return false, "export_round_trip_mismatch"
    end
    return true
end

ExportCodec.format = FORMAT
ExportCodec.eventsPerBlock = EVENTS_PER_BLOCK

return ExportCodec
