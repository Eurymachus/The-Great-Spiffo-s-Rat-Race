local Identity = {}
local CharacterSnapshot = require "TGSRR/Run/CharacterSnapshot"

local MOD_DATA_KEY = "TGSRR_Run"
local SCHEMA_VERSION = 11

local CHALLENGE_MODES = {
    TGSRR = "standard",
    TGSRR_CDDA = "cdda",
    TGSRR_Sprinters = "sprinters",
}

local GAME_MODE_IDS = {
    ["The Great Spiffo's Rat Race"] = "TGSRR",
    ["The Great Spiffo's Rat Race - CDDA"] = "TGSRR_CDDA",
    ["The Great Spiffo's Rat Race - Sprinters"] = "TGSRR_Sprinters",
}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

local function utcSeconds()
    return math.floor(tonumber(os.time()) or 0)
end

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
    end
    data.sessionSequence = tonumber(data.sessionSequence) or 0
    data.lastModIds = type(data.lastModIds) == "table" and data.lastModIds or {}
    data.lastWorkshopIds = type(data.lastWorkshopIds) == "table" and data.lastWorkshopIds or {}
    data.lastModRefs = type(data.lastModRefs) == "table" and data.lastModRefs or nil
    data.eventSequence = tonumber(data.eventSequence) or 0
    data.eventHash = nonEmpty(data.eventHash) or string.rep("0", 64)
    data.dailyState = type(data.dailyState) == "table" and data.dailyState or nil
    data.providerIds = nil -- discard obsolete pre-release integration state
    return data
end

local function challengeEvidence()
    local core = getCore and getCore() or nil
    return {
        id = core and core.getChallengeID and nonEmpty(core:getChallengeID()) or "",
        gameMode = core and core.getGameMode and nonEmpty(core:getGameMode()) or "",
    }
end

local function recognizedChallengeId()
    local evidence = challengeEvidence()
    local id = nonEmpty(evidence.id)
    if id and CHALLENGE_MODES[id] then return id end
    return GAME_MODE_IDS[nonEmpty(evidence.gameMode)]
end

function Identity.isRatRaceChallenge()
    return CHALLENGE_MODES[recognizedChallengeId()] ~= nil
end

local function newRunId()
    local utc = utcSeconds()
    local millis = getTimestampMs and getTimestampMs() or (utc * 1000)
    local millisText = string.format("%.0f", tonumber(millis) or (utc * 1000))
    local randomA = ZombRand(100000, 999999)
    local randomB = ZombRand(100000, 999999)
    return string.format("rr-%d-%s-%06d-%06d", utc, millisText, randomA, randomB)
end

function Identity.ensure(player, selectedTraitSnapshot)
    if not player then return nil, false end
    local data = root()
    if not nonEmpty(data.runId) and not Identity.isRatRaceChallenge() then
        return nil, false
    end
    local created = false
    if not nonEmpty(data.runId) then
        local challenge = challengeEvidence()
        local gameTime = getGameTime()
        local character = CharacterSnapshot.observe(player)

        data.runId = newRunId()
        data.createdUtc = utcSeconds()
        data.createdWorldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
        data.bootstrapped = player.getHoursSurvived and player:getHoursSurvived() > 0 or false
        data.lifecycle = "active"
        data.epoch = 1
        data.startingChallenge = challenge
        data.startingCharacter = character.name
        data.selectedStartingTraits = selectedTraitSnapshot
            and selectedTraitSnapshot.traits or character.traits
        data.selectedStartingTraitsPartial = selectedTraitSnapshot == nil
        data.selectedStartingTraitsCapturedUtc = selectedTraitSnapshot
            and selectedTraitSnapshot.capturedUtc or data.createdUtc
        data.startingEffectiveTraits = character.traits
        data.sessionSequence = 0
        data.lastModIds = {}
        data.lastWorkshopIds = {}
        data.lastModRefs = {}
        data.eventSequence = 0
        data.eventHash = string.rep("0", 64)
        data.dailyState = nil
        data.weaponKills = {}
        data.weaponKillsPartial = data.bootstrapped
        data.weaponKillsBaselineTotal =
            math.max(0, tonumber(player:getZombieKills()) or 0)
        data.fireDeaths = 0
        data.fireDeathsPartial = data.bootstrapped
        data.townVisits = {}
        data.townVisitsPartial = data.bootstrapped
        data.distanceTravelledMeters = 0
        data.distanceRejectedSamples = 0
        data.distanceTravelledPartial = data.bootstrapped
        data.brokenWeapons = {}
        data.brokenWeaponsTotal = 0
        data.brokenWeaponsPartial = data.bootstrapped
        data.animalsSlaughtered = {}
        data.animalsSlaughteredTotal = 0
        data.animalsSlaughteredPartial = data.bootstrapped
        data.integrityStatus = "unverified"
        created = true
    end

    if type(data.startingChallenge) ~= "table" then
        data.startingChallenge = {
            id = nonEmpty(data.challengeId) or "",
            gameMode = nonEmpty(data.gameMode) or "",
        }
        data.startingChallengePartial = true
    end
    local observedChallenge = challengeEvidence()
    if not nonEmpty(data.startingChallenge.id)
            and nonEmpty(observedChallenge.id) then
        data.startingChallenge.id = observedChallenge.id
    end
    if not nonEmpty(data.startingChallenge.gameMode)
            and nonEmpty(observedChallenge.gameMode) then
        data.startingChallenge.gameMode = observedChallenge.gameMode
    end
    data.classification = nil
    data.challengeId = nil
    data.challengeMode = nil
    data.gameMode = nil

    if type(data.selectedStartingTraits) ~= "table" then
        local legacy = type(data.startingTraits) == "table"
            and data.startingTraits or CharacterSnapshot.traits(player)
        data.selectedStartingTraits = legacy
        data.selectedStartingTraitsPartial = true
        data.selectedStartingTraitsCapturedUtc = data.createdUtc
    end
    if type(data.startingEffectiveTraits) ~= "table" then
        data.startingEffectiveTraits = type(data.startingTraits) == "table"
            and data.startingTraits or CharacterSnapshot.traits(player)
    end
    data.startingTraits = nil
    data.startingTraitsPartial = nil

    if type(data.weaponKills) ~= "table" then
        data.weaponKills = {}
        data.weaponKillsPartial = true
        data.weaponKillsBaselineTotal =
            math.max(0, tonumber(player:getZombieKills()) or 0)
    end
    if data.fireDeaths == nil then
        data.fireDeaths = 0
        data.fireDeathsPartial = true
    else
        data.fireDeaths = math.max(0,
            math.floor(tonumber(data.fireDeaths) or 0))
    end
    if type(data.townVisits) ~= "table" then
        data.townVisits = {}
        data.townVisitsPartial = true
    end
    data.townVisitsPartial = data.townVisitsPartial == true
    if data.distanceTravelledMeters == nil then
        data.distanceTravelledMeters = 0
        data.distanceRejectedSamples = 0
        data.distanceTravelledPartial = true
    else
        data.distanceTravelledMeters =
            math.max(0, tonumber(data.distanceTravelledMeters) or 0)
        data.distanceRejectedSamples = math.max(0,
            math.floor(tonumber(data.distanceRejectedSamples) or 0))
    end
    data.distanceTravelledPartial = data.distanceTravelledPartial == true
    if type(data.brokenWeapons) ~= "table" then
        data.brokenWeapons = {}
        data.brokenWeaponsTotal = 0
        data.brokenWeaponsPartial = true
    else
        data.brokenWeaponsTotal = math.max(0,
            math.floor(tonumber(data.brokenWeaponsTotal) or 0))
    end
    data.brokenWeaponsPartial = data.brokenWeaponsPartial == true
    if type(data.animalsSlaughtered) ~= "table" then
        data.animalsSlaughtered = {}
        data.animalsSlaughteredTotal = 0
        data.animalsSlaughteredPartial = true
    else
        data.animalsSlaughteredTotal = math.max(0,
            math.floor(tonumber(data.animalsSlaughteredTotal) or 0))
    end
    data.animalsSlaughteredPartial =
        data.animalsSlaughteredPartial == true

    return data, created
end

function Identity.observeCharacter(player)
    return CharacterSnapshot.name(player)
end

function Identity.observeTraits(player)
    return CharacterSnapshot.traits(player)
end

function Identity.get()
    local data = root()
    if not nonEmpty(data.runId) then return nil end
    return data
end

function Identity.observeChallenge()
    return challengeEvidence()
end

function Identity.exportChallenge(run)
    local observed = challengeEvidence()
    local starting = type(run) == "table"
        and type(run.startingChallenge) == "table"
        and run.startingChallenge or {}
    return {
        id = nonEmpty(observed.id) or nonEmpty(starting.id) or "",
        gameMode = nonEmpty(observed.gameMode)
            or nonEmpty(starting.gameMode) or "",
    }
end

function Identity.utcSeconds()
    return utcSeconds()
end

return Identity
