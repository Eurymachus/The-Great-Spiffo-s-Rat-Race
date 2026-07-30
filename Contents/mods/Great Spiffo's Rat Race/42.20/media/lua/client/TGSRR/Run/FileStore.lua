local FileStore = {}

local ROOT = "TGSRR/Runs"
local META_FILENAME = "run.meta.txt"
local META_FORMAT = 1
local SESSION_FORMAT = 5

local function encode(value)
    value = tostring(value == nil and "" or value)
    return (value:gsub("%%", "%%25"):gsub("\r", "%%0D"):gsub("\n", "%%0A"):gsub("|", "%%7C"):gsub("=", "%%3D"):gsub(",", "%%2C"))
end

local function decode(value)
    return (tostring(value or ""):gsub("%%2C", ","):gsub("%%3D", "="):gsub("%%7C", "|"):gsub("%%0A", "\n"):gsub("%%0D", "\r"):gsub("%%25", "%%"))
end

local function path(runId, filename)
    return ROOT .. "/" .. tostring(runId) .. "/" .. filename
end

local function readMeta(runId)
    local reader = getFileReader(path(runId, META_FILENAME), false)
    if not reader then return nil end
    local result = {}
    local line = reader:readLine()
    while line do
        local key, value = line:match("^([^=]+)=(.*)$")
        if key then result[key] = decode(value) end
        line = reader:readLine()
    end
    reader:close()
    return result
end

local function writeMeta(run)
    local writer = getFileWriter(path(run.runId, META_FILENAME), true, false)
    if not writer then return false, "unable to create " .. META_FILENAME end

    local fields = {
        { "format", META_FORMAT },
        { "runId", run.runId },
        { "createdUtc", run.createdUtc },
        { "createdWorldAgeHours", run.createdWorldAgeHours },
        { "bootstrapped", run.bootstrapped and "true" or "false" },
        { "lifecycle", run.lifecycle },
        { "epoch", run.epoch },
        { "startingChallengeId", run.startingChallenge and run.startingChallenge.id },
        { "startingGameMode", run.startingChallenge and run.startingChallenge.gameMode },
        { "startingChallengePartial", run.startingChallengePartial and "true" or "false" },
        { "forename", run.startingCharacter and run.startingCharacter.forename },
        { "surname", run.startingCharacter and run.startingCharacter.surname },
        { "displayName", run.startingCharacter and run.startingCharacter.displayName },
        { "professionId", run.startingCharacter and run.startingCharacter.professionId },
    }
    for _, field in ipairs(fields) do
        writer:write(field[1] .. "=" .. encode(field[2]) .. "\n")
    end
    writer:close()
    return true
end

function FileStore.initialize(run, created)
    local meta = readMeta(run.runId)
    if not meta then
        if not created then return false, "missing_run_meta" end
        local ok, err = writeMeta(run)
        if not ok then return false, err end
        return true, "created"
    end
    if tonumber(meta.format) ~= META_FORMAT then return false, "unsupported_meta_format" end
    if meta.runId ~= tostring(run.runId) then return false, "run_id_mismatch" end
    return true, "matched"
end

function FileStore.sessionHead(runId)
    local reader = getFileReader(path(runId, "sessions.log"), false)
    if not reader then return nil, "missing_session_history" end
    local lastSequence = nil
    local line = reader:readLine()
    while line do
        local encodedSequence = line:match("^S%d+|seq=([^|]+)")
        if encodedSequence then lastSequence = tonumber(decode(encodedSequence)) end
        line = reader:readLine()
    end
    reader:close()
    if lastSequence == nil then return nil, "invalid_session_history" end
    return lastSequence
end

local function encodeList(values)
    local encoded = {}
    for i = 1, #values do encoded[i] = encode(values[i]) end
    return table.concat(encoded, ",")
end

local function modReferenceFields(mods)
    local values = {}
    for _, mod in ipairs(mods or {}) do
        values[#values + 1] = encode(mod.modId) .. "=" .. encode(mod.workshopId)
    end
    return table.concat(values, ",")
end

local function changedModReferenceFields(mods)
    local values = {}
    for _, mod in ipairs(mods or {}) do
        values[#values + 1] = table.concat({
            encode(mod.modId),
            encode(mod.previousWorkshopId),
            encode(mod.workshopId),
        }, "=")
    end
    return table.concat(values, ",")
end

function FileStore.lastModReferences(runId)
    local reader = getFileReader(path(runId, "sessions.log"), false)
    if not reader then return nil end
    local encodedReferences = nil
    local line = reader:readLine()
    while line do
        local value = line:match("|modRefs=([^|]*)")
        if value and value ~= "" then encodedReferences = value end
        line = reader:readLine()
    end
    reader:close()
    if not encodedReferences then return nil end

    local references = {}
    for encodedReference in encodedReferences:gmatch("[^,]+") do
        local encodedModId, encodedWorkshopId = encodedReference:match("^([^=]*)=(.*)$")
        if not encodedModId then return nil end
        references[#references + 1] = {
            modId = decode(encodedModId),
            workshopId = decode(encodedWorkshopId),
        }
    end
    table.sort(references, function(a, b) return a.modId < b.modId end)
    return references
end

function FileStore.appendSession(run, session)
    local writer = getFileWriter(path(run.runId, "sessions.log"), true, true)
    if not writer then return false, "unable_to_open_sessions" end
    local fields = {
        "S" .. tostring(SESSION_FORMAT),
        "seq=" .. encode(session.sequence),
        "utc=" .. encode(session.utc),
        "worldAgeHours=" .. encode(session.worldAgeHours),
        "challengeId=" .. encode(session.challenge and session.challenge.id),
        "gameMode=" .. encode(session.challenge and session.challenge.gameMode),
        "forename=" .. encode(session.character.forename),
        "surname=" .. encode(session.character.surname),
        "displayName=" .. encode(session.character.displayName),
        "modState=" .. encode(session.modState),
        "modRefs=" .. modReferenceFields(session.mods),
        "modAddedRefs=" .. modReferenceFields(session.addedMods),
        "modRemovedRefs=" .. modReferenceFields(session.removedMods),
        "modChangedRefs=" .. changedModReferenceFields(session.changedMods),
    }
    writer:write(table.concat(fields, "|") .. "\n")
    writer:close()
    return true
end

return FileStore
