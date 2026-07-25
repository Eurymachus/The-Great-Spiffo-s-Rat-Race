local Identity = require "TGSRR/Run/Identity"
local FileStore = require "TGSRR/Run/FileStore"
local EventCodec = require "TGSRR/Run/EventCodec"
local Ledger = require "TGSRR/Run/Ledger"
local Recorder = require "TGSRR/Run/Recorder"
local EventBridge = require "TGSRR/Run/EventBridge"
local DayTracker = require "TGSRR/Run/DayTracker"
local Exporter = require "TGSRR/Run/Exporter"
local PendingTraitSelection = require "TGSRR/Run/PendingTraitSelection"
local ModSnapshot = require "TGSRR/Run/ModSnapshot"
local WeaponKillTracker = require "TGSRR/Run/WeaponKillTracker"
local TownTracker = require "TGSRR/Run/TownTracker"
local LiteratureTracker = require "TGSRR/Run/LiteratureTracker"
local LocationTracker = require "TGSRR/Run/LocationTracker"
local DistanceTracker = require "TGSRR/Run/DistanceTracker"
require "TGSRR/Run/ExportMenu"

TGSRR = TGSRR or {}
TGSRR.Run = TGSRR.Run or {}
TGSRR.Run.export = function()
    local ok, result = Exporter.generate()
    if ok then
        print("[TGSRR Run] Exported " .. tostring(result.eventSequence) .. " events to "
            .. tostring(result.filename) .. " (" .. tostring(result.encodedCharacters) .. " characters)")
    else
        print("[TGSRR Run] Export failed: " .. tostring(result))
    end
    return ok, result
end

local initialized = false

local function activeMods()
    local mods = ModSnapshot.observe()
    local modIds, workshopIds = ModSnapshot.ids(mods)
    return { mods = mods, modIds = modIds, workshopIds = workshopIds }
end

local function copyList(values)
    local result = {}
    for i = 1, #values do result[i] = values[i] end
    return result
end

local function copyModReferences(values)
    local result = {}
    for _, value in ipairs(values or {}) do
        result[#result + 1] = {
            modId = tostring(value.modId or ""),
            workshopId = tostring(value.workshopId or ""),
        }
    end
    table.sort(result, function(a, b) return a.modId < b.modId end)
    return result
end

local function modReferenceMap(values)
    local result = {}
    for _, value in ipairs(values or {}) do
        result[tostring(value.modId or "")] = tostring(value.workshopId or "")
    end
    return result
end

local function modReferenceDelta(previous, current)
    local previousMap = modReferenceMap(previous)
    local currentMap = modReferenceMap(current)
    local added, removed, changed = {}, {}, {}
    for _, reference in ipairs(current) do
        local previousWorkshopId = previousMap[reference.modId]
        if previousWorkshopId == nil then
            added[#added + 1] = reference
        elseif previousWorkshopId ~= reference.workshopId then
            changed[#changed + 1] = {
                modId = reference.modId,
                previousWorkshopId = previousWorkshopId,
                workshopId = reference.workshopId,
            }
        end
    end
    for _, reference in ipairs(previous) do
        if currentMap[reference.modId] == nil then removed[#removed + 1] = reference end
    end
    return added, removed, changed
end

local function initialize()
    if initialized then return end
    local player = getSpecificPlayer(0)
    if not player then return end
    local existingRun = Identity.get()
    if not existingRun and not Identity.isRatRaceChallenge() then return end
    initialized = true

    local codecOk, codecError = EventCodec.selfTest()
    if not codecOk then
        print("[TGSRR Run] Initialization halted: " .. tostring(codecError))
        return
    end

    local selectedTraitSnapshot = existingRun and nil or PendingTraitSelection.consume(player)
    local run, created = Identity.ensure(player, selectedTraitSnapshot)
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
    EventBridge.install()

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
    local character = Identity.observeCharacter(player)
    local gameTime = getGameTime()
    local nextSequence = (tonumber(run.sessionSequence) or 0) + 1
    local hasPreviousSession = (tonumber(run.sessionSequence) or 0) > 0
    local previousModReferences = run.lastModRefs
    if hasPreviousSession and type(previousModReferences) ~= "table" then
        previousModReferences = FileStore.lastModReferences(run.runId)
    end
    previousModReferences = copyModReferences(previousModReferences or {})
    local addedMods, removedMods, changedMods =
        modReferenceDelta(previousModReferences, current.mods)

    local session = {
        sequence = nextSequence,
        utc = Identity.utcSeconds(),
        worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0,
        character = character,
        challenge = Identity.observeChallenge(),
        modState = hasPreviousSession and "delta" or "baseline",
        mods = hasPreviousSession and {} or current.mods,
        addedMods = hasPreviousSession and addedMods or {},
        removedMods = hasPreviousSession and removedMods or {},
        changedMods = hasPreviousSession and changedMods or {},
    }

    local ledgerAppended, ledgerResult = Recorder.record("session.started", {
        sessionSequence = session.sequence,
        character = session.character,
        challenge = session.challenge,
        modState = session.modState,
        mods = session.mods,
        addedMods = session.addedMods,
        removedMods = session.removedMods,
        changedMods = session.changedMods,
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
    run.lastModRefs = copyModReferences(current.mods)
    run.integrityStatus = "ok"
    WeaponKillTracker.initialize(run, player)
    TownTracker.initialize(run, player)
    LocationTracker.initialize(run, player, created)
    DistanceTracker.initialize(run, player)
    local literatureReady, literatureError =
        LiteratureTracker.initialize(run, player, created)
    if not literatureReady then
        run.integrityStatus = literatureError
        print("[TGSRR Run] Literature tracking initialization failed: "
            .. tostring(literatureError))
        return
    end
    local dayReady, dayError = DayTracker.initialize(run, player)
    if not dayReady then
        run.integrityStatus = dayError
        print("[TGSRR Run] Daily tracking initialization failed: " .. tostring(dayError))
        return
    end
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
