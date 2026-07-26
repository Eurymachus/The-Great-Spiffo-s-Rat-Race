local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"

local GeneratorKnowledgeTracker = {}

local RECIPE_ID = "Generator"
local MAGAZINE_ID = "Base.ElectronicsMag4"

local activeRun = nil
local activePlayer = nil
local installed = false
local nextCheckMilliseconds = 0

local function milliseconds()
    if getTimestampMs then return tonumber(getTimestampMs()) or 0 end
    return os.clock() * 1000
end

local function contains(values, wanted)
    for _, value in ipairs(values or {}) do
        if tostring(value) == wanted then return true end
    end
    return false
end

local function magazineCompleted(run)
    local literature = type(run.literature) == "table" and run.literature or {}
    local baseline = type(literature.baseline) == "table"
        and literature.baseline or {}
    return contains(baseline.itemIds, MAGAZINE_ID)
        or type(literature.completed) == "table"
            and type(literature.completed[MAGAZINE_ID]) == "table"
end

local function professionId(player)
    local descriptor = player and player:getDescriptor() or nil
    local profession = descriptor and descriptor:getCharacterProfession() or nil
    local name = profession and profession:getName() or nil
    return name and tostring(name) or ""
end

local function evidence(run, player)
    return {
        professionId = professionId(player),
        electricalLevel = math.max(0,
            math.floor(tonumber(player:getPerkLevel(Perks.Electricity)) or 0)),
        inventive = player:isInventive() == true,
        generatorMagazineCompleted = magazineCompleted(run),
    }
end

local function observeKnown(run, player, knownAtTrackingStart, partial)
    local gameTime = getGameTime()
    local utc = Identity.utcSeconds()
    local worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0
    local survivedHours = math.max(0,
        tonumber(player:getHoursSurvived()) or 0)
    local observedEvidence = evidence(run, player)
    local recorded, event = Recorder.record(
        "knowledge.generator.first_observed",
        {
            recipeId = RECIPE_ID,
            knownAtTrackingStart = knownAtTrackingStart == true,
            partial = partial == true,
            survivedDays = survivedHours / 24,
            evidence = observedEvidence,
        },
        {
            utc = utc,
            worldAgeHours = worldAgeHours,
        }
    )
    if not recorded then return false, event end

    run.generatorKnowledge = {
        schema = 1,
        recipeId = RECIPE_ID,
        known = true,
        knownAtTrackingStart = knownAtTrackingStart == true,
        partial = partial == true,
        firstObservedUtc = event.utc,
        firstObservedWorldAgeHours = event.worldAgeHours,
        survivedDays = survivedHours / 24,
        evidence = observedEvidence,
    }
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Knowledge] First observed Generator recipe"
            .. (knownAtTrackingStart and " (known at tracking start)" or "")
            .. (partial and " (partial)" or ""))
    end
    return true
end

local function check(player)
    if not activeRun or player ~= activePlayer then return end
    local now = milliseconds()
    if now < nextCheckMilliseconds then return end
    nextCheckMilliseconds = now + 1000
    local state = activeRun.generatorKnowledge
    if type(state) == "table" and state.known == true then return end
    if activePlayer:isRecipeActuallyKnown(RECIPE_ID) then
        local partial = state and state.partial == true
            or activeRun.bootstrapped == true
        local ok, reason = observeKnown(activeRun, activePlayer, false, partial)
        if not ok then
            activeRun.integrityStatus = reason
            print("[TGSRR Run] Generator knowledge tracking failed: "
                .. tostring(reason))
        end
    end
end

local function install()
    if installed then return end
    installed = true
    Events.OnPlayerUpdate.Add(check)
end

function GeneratorKnowledgeTracker.initialize(run, player, created)
    activeRun = run
    activePlayer = player
    nextCheckMilliseconds = milliseconds() + 1000
    install()

    if type(run.generatorKnowledge) == "table" then
        run.generatorKnowledge.recipeId = RECIPE_ID
        run.generatorKnowledge.known =
            run.generatorKnowledge.known == true
        run.generatorKnowledge.knownAtTrackingStart =
            run.generatorKnowledge.knownAtTrackingStart == true
        run.generatorKnowledge.partial =
            run.generatorKnowledge.partial == true
        if run.generatorKnowledge.known then return true end
    else
        run.generatorKnowledge = {
            schema = 1,
            recipeId = RECIPE_ID,
            known = false,
            knownAtTrackingStart = false,
            partial = not created or run.bootstrapped == true,
        }
    end

    if player:isRecipeActuallyKnown(RECIPE_ID) then
        return observeKnown(run, player, true,
            not created or run.bootstrapped == true)
    end
    return true
end

return GeneratorKnowledgeTracker
