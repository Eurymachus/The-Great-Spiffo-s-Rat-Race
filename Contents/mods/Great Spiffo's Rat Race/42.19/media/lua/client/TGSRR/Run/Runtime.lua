local Identity = require "TGSRR/Run/Identity"
local FileStore = require "TGSRR/Run/FileStore"
local EventCodec = require "TGSRR/Run/EventCodec"
local Ledger = require "TGSRR/Run/Ledger"
local Recorder = require "TGSRR/Run/Recorder"

local initialized = false

local function activeMods()
    local result = {
        mods = {},
        modIds = {},
        workshopIds = {},
    }
    local workshopSet = {}
    local mods = getActivatedMods and getActivatedMods() or nil
    if mods then
        for index = 0, mods:size() - 1 do
            local modId = tostring(mods:get(index))
            local modInfo = getModInfoByID and getModInfoByID(modId) or nil
            local workshopId = modInfo and modInfo.getWorkshopID and modInfo:getWorkshopID() or nil
            workshopId = workshopId and tostring(workshopId) or ""
            result.mods[#result.mods + 1] = {
                modId = modId,
                workshopId = workshopId,
            }
            result.modIds[#result.modIds + 1] = modId
            if workshopId ~= "" and not workshopSet[workshopId] then
                workshopSet[workshopId] = true
                result.workshopIds[#result.workshopIds + 1] = workshopId
            end
        end
    end
    table.sort(result.mods, function(a, b) return a.modId < b.modId end)
    table.sort(result.modIds)
    table.sort(result.workshopIds)
    return result
end

local function asSet(values)
    local result = {}
    for _, value in ipairs(values or {}) do result[tostring(value)] = true end
    return result
end

local function difference(values, previousSet)
    local result = {}
    for _, value in ipairs(values) do
        if not previousSet[value] then result[#result + 1] = value end
    end
    return result
end

local function copyList(values)
    local result = {}
    for i = 1, #values do result[i] = values[i] end
    return result
end

local function initialize()
    if initialized or not Identity.isRatRaceChallenge() then return end
    local player = getSpecificPlayer(0)
    if not player then return end
    initialized = true

    local codecOk, codecError = EventCodec.selfTest()
    if not codecOk then
        print("[TGSRR Run] Initialization halted: " .. tostring(codecError))
        return
    end

    local run, created = Identity.ensure(player)
    if not run then return end

    local ok, state = FileStore.initialize(run, created)
    if not ok then
        run.integrityStatus = state
        print("[TGSRR Run] Initialization halted: " .. tostring(state))
        return
    end

    local ledgerOk, ledgerError = Ledger.initialize(run)
    if not ledgerOk then
        run.integrityStatus = ledgerError
        print("[TGSRR Run] Initialization halted: " .. tostring(ledgerError))
        return
    end
    Recorder.activate(run)

    if not created then
        local fileSequence, sequenceError = FileStore.sessionHead(run.runId)
        if fileSequence == nil or fileSequence ~= tonumber(run.sessionSequence) then
            run.integrityStatus = sequenceError or "session_cursor_mismatch"
            print("[TGSRR Run] Initialization halted: " .. tostring(run.integrityStatus)
                .. " (save=" .. tostring(run.sessionSequence) .. ", file=" .. tostring(fileSequence) .. ")")
            return
        end
    end

    local current = activeMods()
    local currentMods = current.modIds
    local currentWorkshopIds = current.workshopIds
    local previousMods = copyList(run.lastModIds or {})
    local previousWorkshopIds = copyList(run.lastWorkshopIds or {})
    local previousSet = asSet(previousMods)
    local currentSet = asSet(currentMods)
    local previousWorkshopSet = asSet(previousWorkshopIds)
    local currentWorkshopSet = asSet(currentWorkshopIds)
    local character = Identity.observeCharacter(player)
    local gameTime = getGameTime()
    local nextSequence = (tonumber(run.sessionSequence) or 0) + 1
    local hasPreviousSession = (tonumber(run.sessionSequence) or 0) > 0

    local session = {
        sequence = nextSequence,
        utc = Identity.utcSeconds(),
        worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0,
        character = character,
        mods = current.mods,
        modIds = currentMods,
        addedModIds = hasPreviousSession and difference(currentMods, previousSet) or {},
        removedModIds = hasPreviousSession and difference(previousMods, currentSet) or {},
        workshopIds = currentWorkshopIds,
        addedWorkshopIds = hasPreviousSession and difference(currentWorkshopIds, previousWorkshopSet) or {},
        removedWorkshopIds = hasPreviousSession and difference(previousWorkshopIds, currentWorkshopSet) or {},
    }

    local ledgerAppended, ledgerResult = Recorder.record("session.started", {
        sessionSequence = session.sequence,
        character = session.character,
        mods = session.mods,
        addedModIds = session.addedModIds,
        removedModIds = session.removedModIds,
        addedWorkshopIds = session.addedWorkshopIds,
        removedWorkshopIds = session.removedWorkshopIds,
    }, {
        utc = session.utc,
        worldAgeHours = session.worldAgeHours,
    })
    if not ledgerAppended then
        run.integrityStatus = ledgerResult
        print("[TGSRR Run] Ledger append failed: " .. tostring(ledgerResult))
        return
    end

    local appended, appendError = FileStore.appendSession(run, session)
    if not appended then
        Recorder.deactivate()
        run.integrityStatus = appendError
        print("[TGSRR Run] Session append failed: " .. tostring(appendError))
        return
    end

    run.sessionSequence = nextSequence
    run.lastModIds = copyList(currentMods)
    run.lastWorkshopIds = copyList(currentWorkshopIds)
    run.integrityStatus = "ok"
    print("[TGSRR Run] " .. (created and "Created" or "Loaded") .. " run " .. tostring(run.runId)
        .. ", session " .. tostring(nextSequence) .. (run.bootstrapped and " (bootstrapped)" or ""))
end

Events.OnGameStart.Add(initialize)
Events.OnCreatePlayer.Add(function(playerNum)
    if playerNum == 0 then initialize() end
end)

return {
    initialize = initialize,
}
