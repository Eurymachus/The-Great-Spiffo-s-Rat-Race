local Identity = {}

local MOD_DATA_KEY = "TGSRR_Run"
local SCHEMA_VERSION = 3

local CHALLENGE_MODES = {
    TGSRR = "standard",
    TGSRR_CDDA = "cdda",
    TGSRR_Sprinters = "sprinters",
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
    data.eventSequence = tonumber(data.eventSequence) or 0
    data.eventHash = nonEmpty(data.eventHash) or string.rep("0", 64)
    data.providerIds = nil -- discard obsolete pre-release integration state
    return data
end

local function challengeId()
    local core = getCore and getCore() or nil
    if not core or not core.isChallenge or not core:isChallenge() then return nil end
    return nonEmpty(core:getChallengeID())
end

function Identity.isRatRaceChallenge()
    return CHALLENGE_MODES[challengeId()] ~= nil
end

local function characterName(player)
    local descriptor = player and player.getDescriptor and player:getDescriptor() or nil
    local forename = descriptor and nonEmpty(descriptor:getForename()) or "Unknown"
    local surname = descriptor and nonEmpty(descriptor:getSurname()) or ""
    local displayName = forename
    if surname ~= "" then displayName = displayName .. " " .. surname end
    return {
        forename = forename,
        surname = surname,
        displayName = displayName,
    }
end

local function newRunId()
    local utc = utcSeconds()
    local millis = getTimestampMs and getTimestampMs() or (utc * 1000)
    local millisText = string.format("%.0f", tonumber(millis) or (utc * 1000))
    local randomA = ZombRand(100000, 999999)
    local randomB = ZombRand(100000, 999999)
    return string.format("rr-%d-%s-%06d-%06d", utc, millisText, randomA, randomB)
end

function Identity.ensure(player)
    if not Identity.isRatRaceChallenge() or not player then return nil, false end

    local data = root()
    local created = false
    if not nonEmpty(data.runId) then
        local id = challengeId()
        local core = getCore()
        local gameTime = getGameTime()
        local name = characterName(player)

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
        data.startingCharacter = name
        data.sessionSequence = 0
        data.lastModIds = {}
        data.lastWorkshopIds = {}
        data.eventSequence = 0
        data.eventHash = string.rep("0", 64)
        data.integrityStatus = "unverified"
        created = true
    end

    return data, created
end

function Identity.observeCharacter(player)
    return characterName(player)
end

function Identity.get()
    local data = root()
    if not nonEmpty(data.runId) then return nil end
    return data
end

function Identity.getChallengeMode(id)
    return CHALLENGE_MODES[id]
end

function Identity.utcSeconds()
    return utcSeconds()
end

return Identity
