local Identity = {}
local CharacterSnapshot = require "TGSRR/Run/CharacterSnapshot"

local MOD_DATA_KEY = "TGSRR_Run"
local SCHEMA_VERSION = 7

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

local function challengeId()
    local core = getCore and getCore() or nil
    if not core then return nil end
    local id = core.isChallenge and core:isChallenge()
        and core.getChallengeID and nonEmpty(core:getChallengeID()) or nil
    if id and CHALLENGE_MODES[id] then return id end
    local gameMode = core.getGameMode and nonEmpty(core:getGameMode()) or nil
    return GAME_MODE_IDS[gameMode]
end

function Identity.isRatRaceChallenge()
    return CHALLENGE_MODES[challengeId()] ~= nil
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
    if not Identity.isRatRaceChallenge() or not player then return nil, false end

    local data = root()
    local created = false
    if not nonEmpty(data.runId) then
        local id = challengeId()
        local core = getCore()
        local gameTime = getGameTime()
        local character = CharacterSnapshot.observe(player)

        data.runId = newRunId()
        data.createdUtc = utcSeconds()
        data.createdWorldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
        data.bootstrapped = player.getHoursSurvived and player:getHoursSurvived() > 0 or false
        data.lifecycle = "active"
        data.classification = "unclassified"
        data.epoch = 1
        data.challengeId = id
        data.challengeMode = CHALLENGE_MODES[id]
        data.gameMode = core and nonEmpty(core:getGameMode()) or nil
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
        data.integrityStatus = "unverified"
        created = true
    end

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

function Identity.getChallengeMode(id)
    return CHALLENGE_MODES[id]
end

function Identity.getChallengeId()
    return challengeId()
end

function Identity.utcSeconds()
    return utcSeconds()
end

return Identity
