local FileStore = {}

local ROOT = "TGSRR/Runs"
local META_FORMAT = 1
local SESSION_FORMAT = 3

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
    local reader = getFileReader(path(runId, "run.meta"), false)
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
    local writer = getFileWriter(path(run.runId, "run.meta"), true, false)
    if not writer then return false, "unable to create run.meta" end

    local fields = {
        { "format", META_FORMAT },
        { "runId", run.runId },
        { "createdUtc", run.createdUtc },
        { "createdWorldAgeHours", run.createdWorldAgeHours },
        { "bootstrapped", run.bootstrapped and "true" or "false" },
        { "lifecycle", run.lifecycle },
        { "classification", run.classification },
        { "epoch", run.epoch },
        { "challengeId", run.challengeId },
        { "challengeMode", run.challengeMode },
        { "gameMode", run.gameMode },
        { "forename", run.startingCharacter and run.startingCharacter.forename },
        { "surname", run.startingCharacter and run.startingCharacter.surname },
        { "displayName", run.startingCharacter and run.startingCharacter.displayName },
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

function FileStore.appendSession(run, session)
    local writer = getFileWriter(path(run.runId, "sessions.log"), true, true)
    if not writer then return false, "unable_to_open_sessions" end
    local fields = {
        "S" .. tostring(SESSION_FORMAT),
        "seq=" .. encode(session.sequence),
        "utc=" .. encode(session.utc),
        "worldAgeHours=" .. encode(session.worldAgeHours),
        "challengeId=" .. encode(run.challengeId),
        "gameMode=" .. encode(run.gameMode),
        "forename=" .. encode(session.character.forename),
        "surname=" .. encode(session.character.surname),
        "displayName=" .. encode(session.character.displayName),
        "modRefs=" .. modReferenceFields(session.mods),
        "mods=" .. encodeList(session.modIds),
        "added=" .. encodeList(session.addedModIds),
        "removed=" .. encodeList(session.removedModIds),
        "workshopIds=" .. encodeList(session.workshopIds),
        "workshopAdded=" .. encodeList(session.addedWorkshopIds),
        "workshopRemoved=" .. encodeList(session.removedWorkshopIds),
    }
    writer:write(table.concat(fields, "|") .. "\n")
    writer:close()
    return true
end

return FileStore
