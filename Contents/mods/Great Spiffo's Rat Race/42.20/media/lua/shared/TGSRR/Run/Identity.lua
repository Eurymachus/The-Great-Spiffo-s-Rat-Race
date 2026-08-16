local Identity = {}
local CharacterSnapshot = require "TGSRR/Run/CharacterSnapshot"
local StartingLocation = require "TGSRR/Run/StartingLocation"
local SelectedChallenge = require "TGSRR/Run/SelectedChallenge"
local ChallengeContext = require "TGSRR/Challenge/Context"

local MOD_DATA_KEY = "TGSRR_Run"
local SCHEMA_VERSION = 22
local CONTRACT_VERSION = 1
local pendingDevelopmentReset = nil

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
    local incompatible = nil
    if nonEmpty(data.runId)
            and tonumber(data.schemaVersion) ~= SCHEMA_VERSION then
        incompatible = "unsupported_run_schema:"
            .. tostring(data.schemaVersion)
    elseif nonEmpty(data.runId)
            and tonumber(data.contractVersion) ~= CONTRACT_VERSION then
        incompatible = "unsupported_run_contract:"
            .. tostring(data.contractVersion)
    end
    if incompatible then
        local oldRunId = tostring(data.runId)
        ModData.remove(MOD_DATA_KEY)
        data = ModData.getOrCreate(MOD_DATA_KEY)
        pendingDevelopmentReset = {
            reason = incompatible,
            oldRunId = oldRunId,
        }
        print("[TGSRR Run] TEMPORARY RESET: removed incompatible TGSRR_Run "
            .. oldRunId .. " (" .. incompatible .. ")")
    end
    if not nonEmpty(data.runId) then
        for key in pairs(data) do data[key] = nil end
        data.schemaVersion = SCHEMA_VERSION
        data.contractVersion = CONTRACT_VERSION
    end
    data.sessionSequence = tonumber(data.sessionSequence) or 0
    data.lastModIds = type(data.lastModIds) == "table" and data.lastModIds or {}
    data.lastWorkshopIds = type(data.lastWorkshopIds) == "table" and data.lastWorkshopIds or {}
    data.lastModRefs = type(data.lastModRefs) == "table" and data.lastModRefs or nil
    data.eventSequence = tonumber(data.eventSequence) or 0
    data.eventHash = nonEmpty(data.eventHash) or string.rep("0", 64)
    data.dailyState = type(data.dailyState) == "table" and data.dailyState or nil
    return data
end

local function challengeEvidence()
    local core = getCore and getCore() or nil
    local gameMode =
        core and core.getGameMode and nonEmpty(core:getGameMode()) or ""
    local captured = SelectedChallenge.observe(gameMode)
    local selected = LastStandData
        and type(LastStandData.chosenChallenge) == "table"
        and LastStandData.chosenChallenge or nil
    local selectedGameMode = selected and nonEmpty(selected.gameMode)
    local selectedId = selectedGameMode
        and selectedGameMode == nonEmpty(gameMode)
        and nonEmpty(selected.id) or nil
    return {
        id = (captured and nonEmpty(captured.id))
            or selectedId
            or (core and core.getChallengeID
                and nonEmpty(core:getChallengeID()) or ""),
        gameMode = gameMode,
    }
end

local function recognizedChallengeId()
    local evidence = challengeEvidence()
    local id = nonEmpty(evidence.id)
    if id and CHALLENGE_MODES[id] then return id end
    return GAME_MODE_IDS[nonEmpty(evidence.gameMode)]
end

function Identity.isRatRaceChallenge()
    return ChallengeContext.isActive()
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
    local data, rootError = root()
    if not data then return nil, false, rootError end
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
        data.startingCharacter = character.identity
        data.startingLocation = StartingLocation.observe(player,
            data.createdUtc, data.createdWorldAgeHours, data.bootstrapped)
        data.chosenStartingRegion = selectedTraitSnapshot
            and selectedTraitSnapshot.chosenStartingRegion or nil
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
        data.parentEpoch = nil
        data.branchCheckpointSequence = nil
        data.branchCheckpointHash = nil
        data.dailyState = nil
        data.weaponKills = {}
        data.weaponKillsPartial = data.bootstrapped
        data.weaponKillsBaselineTotal =
            math.max(0, tonumber(player:getZombieKills()) or 0)
        data.fireDeaths = 0
        data.fireDeathsPartial = data.bootstrapped
        data.zombieKillTypes = {}
        data.zombieKillTypesPartial = data.bootstrapped
        data.townVisits = {}
        data.townVisitsPartial = data.bootstrapped
        data.buildingVisits = {}
        data.buildingVisitsPartial = data.bootstrapped
        data.distanceTravelledMeters = 0
        data.distanceRejectedSamples = 0
        data.distanceTravelledPartial = data.bootstrapped
        data.nimbleStanceMovementMilliseconds = 0
        data.nimbleStanceMovementPartial = data.bootstrapped
        data.activeGameplayMilliseconds = 0
        data.activeGameplayPartial = data.bootstrapped
        data.brokenWeapons = {}
        data.brokenWeaponsTotal = 0
        data.brokenWeaponsPartial = data.bootstrapped
        data.animalsSlaughtered = {}
        data.animalsSlaughteredTotal = 0
        data.animalsSlaughteredPartial = data.bootstrapped
        data.animalsTrapped = {}
        data.animalsTrappedTotal = 0
        data.animalsTrappedPartial = data.bootstrapped
        data.animalBirths = {}
        data.animalBirthsTotal = 0
        data.animalBirthsPartial = data.bootstrapped
        data.animalsPetted = {}
        data.animalsPettedTotal = 0
        data.animalsPettedPartial = data.bootstrapped
        data.milkCollected = {}
        data.milkCollectedTotal = 0
        data.milkCollectedPartial = data.bootstrapped
        data.fluidConsumed = {}
        data.fluidConsumedTotal = 0
        data.fluidConsumedPartial = data.bootstrapped
        data.caloriesConsumed = 0
        data.caloriesConsumedPartial = data.bootstrapped
        data.butterProduced = 0
        data.butterProducedPartial = data.bootstrapped
        data.butterChurns = {}
        data.fishCaught = {}
        data.fishCaughtTotal = 0
        data.fishCaughtPartial = data.bootstrapped
        data.animalIdentities = {}
        data.animalIdentityByPzId = {}
        data.animalIdentitySequence = 0
        data.animalBirthTrackingInitialized = false
        data.generatorKnowledge = nil
        data.generatorRepairs = 0
        data.generatorConditionRestored = 0
        data.generatorRepairsPartial = data.bootstrapped
        data.injuries = {}
        data.injuriesTotal = 0
        data.injuriesPartial = data.bootstrapped
        data.zombieAssociatedInjuries = {}
        data.zombieAssociatedInjuriesTotal = 0
        data.injuryObservedState = nil
        data.integrityStatus = "unverified"
        created = true
    end

    if type(data.startingChallenge) ~= "table" then
        return nil, false, "invalid_current_run_state:startingChallenge"
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
    if type(data.selectedStartingTraits) ~= "table" then
        return nil, false,
            "invalid_current_run_state:selectedStartingTraits"
    end
    if type(data.startingEffectiveTraits) ~= "table" then
        return nil, false,
            "invalid_current_run_state:startingEffectiveTraits"
    end

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
    if type(data.zombieKillTypes) ~= "table" then
        data.zombieKillTypes = {}
        data.zombieKillTypesPartial = true
    end
    data.zombieKillTypesPartial = data.zombieKillTypesPartial == true
    if type(data.townVisits) ~= "table" then
        data.townVisits = {}
        data.townVisitsPartial = true
    end
    data.townVisitsPartial = data.townVisitsPartial == true
    if type(data.buildingVisits) ~= "table" then
        data.buildingVisits = {}
        data.buildingVisitsPartial = true
    end
    data.buildingVisitsPartial = data.buildingVisitsPartial == true
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
    if data.nimbleStanceMovementMilliseconds == nil then
        data.nimbleStanceMovementMilliseconds = 0
        data.nimbleStanceMovementPartial = true
    else
        data.nimbleStanceMovementMilliseconds = math.max(0,
            tonumber(data.nimbleStanceMovementMilliseconds) or 0)
    end
    data.nimbleStanceMovementPartial =
        data.nimbleStanceMovementPartial == true
    if data.activeGameplayMilliseconds == nil then
        data.activeGameplayMilliseconds = 0
        data.activeGameplayPartial = true
    else
        data.activeGameplayMilliseconds = math.max(0,
            tonumber(data.activeGameplayMilliseconds) or 0)
    end
    data.activeGameplayPartial = data.activeGameplayPartial == true
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
    if type(data.animalsTrapped) ~= "table" then
        data.animalsTrapped = {}
        data.animalsTrappedTotal = 0
        data.animalsTrappedPartial = true
    else
        data.animalsTrappedTotal = math.max(0,
            math.floor(tonumber(data.animalsTrappedTotal) or 0))
    end
    data.animalsTrappedPartial = data.animalsTrappedPartial == true
    if type(data.animalBirths) ~= "table" then
        data.animalBirths = {}
        data.animalBirthsTotal = 0
        data.animalBirthsPartial = true
        data.animalBirthTrackingInitialized = false
    else
        data.animalBirthsTotal = math.max(0,
            math.floor(tonumber(data.animalBirthsTotal) or 0))
    end
    data.animalBirthsPartial = data.animalBirthsPartial == true
    if type(data.animalsPetted) ~= "table" then
        data.animalsPetted = {}
        data.animalsPettedTotal = 0
        data.animalsPettedPartial = true
    else
        data.animalsPettedTotal = math.max(0,
            math.floor(tonumber(data.animalsPettedTotal) or 0))
    end
    data.animalsPettedPartial = data.animalsPettedPartial == true
    if type(data.milkCollected) ~= "table" then
        data.milkCollected = {}
        data.milkCollectedTotal = 0
        data.milkCollectedPartial = true
    else
        data.milkCollectedTotal =
            math.max(0, tonumber(data.milkCollectedTotal) or 0)
    end
    data.milkCollectedPartial = data.milkCollectedPartial == true
    if type(data.fluidConsumed) ~= "table" then
        data.fluidConsumed = {}
        data.fluidConsumedTotal = 0
        data.fluidConsumedPartial = true
    else
        data.fluidConsumedTotal =
            math.max(0, tonumber(data.fluidConsumedTotal) or 0)
    end
    data.fluidConsumedPartial = data.fluidConsumedPartial == true
    if data.caloriesConsumed == nil then
        data.caloriesConsumed = 0
        data.caloriesConsumedPartial = true
    else
        data.caloriesConsumed =
            math.max(0, tonumber(data.caloriesConsumed) or 0)
    end
    data.caloriesConsumedPartial =
        data.caloriesConsumedPartial == true
    if data.butterProduced == nil then
        data.butterProduced = 0
        data.butterProducedPartial = true
    else
        data.butterProduced = math.max(0,
            math.floor(tonumber(data.butterProduced) or 0))
    end
    data.butterProducedPartial = data.butterProducedPartial == true
    data.butterChurns = type(data.butterChurns) == "table"
        and data.butterChurns or {}
    if type(data.fishCaught) ~= "table" then
        data.fishCaught = {}
        data.fishCaughtTotal = 0
        data.fishCaughtPartial = true
    else
        data.fishCaughtTotal = math.max(0,
            math.floor(tonumber(data.fishCaughtTotal) or 0))
    end
    data.fishCaughtPartial = data.fishCaughtPartial == true
    data.animalIdentities = type(data.animalIdentities) == "table"
        and data.animalIdentities or {}
    data.animalIdentityByPzId =
        type(data.animalIdentityByPzId) == "table"
            and data.animalIdentityByPzId or {}
    data.animalIdentitySequence = math.max(0,
        math.floor(tonumber(data.animalIdentitySequence) or 0))
    data.animalBirthTrackingInitialized =
        data.animalBirthTrackingInitialized == true
    if data.generatorRepairs == nil then
        data.generatorRepairs = 0
        data.generatorConditionRestored = 0
        data.generatorRepairsPartial = true
    else
        data.generatorRepairs = math.max(0,
            math.floor(tonumber(data.generatorRepairs) or 0))
        data.generatorConditionRestored = math.max(0,
            tonumber(data.generatorConditionRestored) or 0)
    end
    data.generatorRepairsPartial =
        data.generatorRepairsPartial == true
    if type(data.injuries) ~= "table" then
        data.injuries = {}
        data.injuriesTotal = 0
        data.injuriesPartial = true
        data.injuryObservedState = nil
    else
        data.injuriesTotal = math.max(0,
            math.floor(tonumber(data.injuriesTotal) or 0))
    end
    data.injuriesPartial = data.injuriesPartial == true
    data.zombieAssociatedInjuries =
        type(data.zombieAssociatedInjuries) == "table"
            and data.zombieAssociatedInjuries or {}
    data.zombieAssociatedInjuriesTotal = math.max(0,
        math.floor(tonumber(data.zombieAssociatedInjuriesTotal) or 0))
    data.injuryObservedState = type(data.injuryObservedState) == "table"
        and data.injuryObservedState or nil

    data.epoch = math.max(1,
        math.floor(tonumber(data.epoch) or 1))
    if data.epoch > 1 then
        data.parentEpoch = math.max(1,
            math.floor(tonumber(data.parentEpoch) or (data.epoch - 1)))
        data.branchCheckpointSequence = math.max(0,
            math.floor(tonumber(data.branchCheckpointSequence) or 0))
        data.branchCheckpointHash =
            tostring(data.branchCheckpointHash or ""):lower()
    else
        data.parentEpoch = nil
        data.branchCheckpointSequence = nil
        data.branchCheckpointHash = nil
    end

    return data, created
end

function Identity.observeCharacter(player)
    return CharacterSnapshot.identity(player)
end

function Identity.observeTraits(player)
    return CharacterSnapshot.traits(player)
end

function Identity.get()
    local data, rootError = root()
    if not data then return nil, rootError end
    if not nonEmpty(data.runId) then return nil end
    return data
end

function Identity.consumeDevelopmentReset()
    local value = pendingDevelopmentReset
    pendingDevelopmentReset = nil
    return value
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
