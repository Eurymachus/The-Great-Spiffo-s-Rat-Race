local Identity = require "TGSRR/Run/Identity"
local Ledger = require "TGSRR/Run/Ledger"
local ExportCodec = require "TGSRR/Run/ExportCodec"
local SkillSnapshot = require "TGSRR/Run/SkillSnapshot"
local OutpostSnapshot = require "TGSRR/Run/OutpostSnapshot"
local OutpostLifecycleSnapshot = require "TGSRR/Run/OutpostLifecycleSnapshot"
local ChallengeProgressSnapshot = require "TGSRR/Run/ChallengeProgressSnapshot"
local ModSnapshot = require "TGSRR/Run/ModSnapshot"
local DailySnapshot = require "TGSRR/Run/DailySnapshot"
local WeaponKillSnapshot = require "TGSRR/Run/WeaponKillSnapshot"
local TownSnapshot = require "TGSRR/Run/TownSnapshot"
local LiteratureSnapshot = require "TGSRR/Run/LiteratureSnapshot"
local LocationSnapshot = require "TGSRR/Run/LocationSnapshot"
local MilestoneSnapshot = require "TGSRR/Run/MilestoneSnapshot"
local BrokenWeaponSnapshot = require "TGSRR/Run/BrokenWeaponSnapshot"
local AnimalSlaughterSnapshot = require "TGSRR/Run/AnimalSlaughterSnapshot"
local AnimalTrapSnapshot = require "TGSRR/Run/AnimalTrapSnapshot"
local AnimalBirthSnapshot = require "TGSRR/Run/AnimalBirthSnapshot"
local AnimalPetSnapshot = require "TGSRR/Run/AnimalPetSnapshot"
local GeneratorKnowledgeSnapshot =
    require "TGSRR/Run/GeneratorKnowledgeSnapshot"
local InjurySnapshot = require "TGSRR/Run/InjurySnapshot"
local MilkSnapshot = require "TGSRR/Run/MilkSnapshot"
local FluidConsumedSnapshot =
    require "TGSRR/Run/FluidConsumedSnapshot"
local FishCaughtSnapshot = require "TGSRR/Run/FishCaughtSnapshot"

local Exporter = {}

local ROOT = "TGSRR/Runs"
local SLICE_MILLISECONDS = 8
local codecSelfTestPassed = false

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function copyList(values)
    local result = {}
    for index, value in ipairs(values or {}) do result[index] = tostring(value) end
    return result
end

local function omitFalsePartialFlags(value)
    if type(value) ~= "table" then return end
    for key, child in pairs(value) do
        local name = tostring(key)
        if child == false and (name == "partial"
                or string.sub(name, -7) == "Partial") then
            value[key] = nil
        elseif type(child) == "table" then
            omitFalsePartialFlags(child)
        end
    end
end

local function omitEmptyKillEvidence(projection)
    local weaponKills = projection.weaponKills or {}
    if weaponKills.partial ~= true
            and (tonumber(weaponKills.baselineTotal) or 0) == 0
            and #(weaponKills.sources or {}) == 0 then
        projection.weaponKills = nil
    end
    local fireDeaths = projection.fireDeaths or {}
    if fireDeaths.partial ~= true
            and (tonumber(fireDeaths.count) or 0) == 0 then
        projection.fireDeaths = nil
    end
    local killTypes = projection.zombieKillTypes or {}
    if killTypes.partial ~= true
            and (tonumber(killTypes.standing) or 0) == 0
            and (tonumber(killTypes.onfront) or 0) == 0
            and (tonumber(killTypes.onback) or 0) == 0
            and (tonumber(killTypes.fenceAssist) or 0) == 0
            and (tonumber(killTypes.windowAssist) or 0) == 0 then
        projection.zombieKillTypes = nil
    end
end

local function characterProjection(run, player)
    return {
        starting = run.startingCharacter or {},
        chosenStartingRegion = run.chosenStartingRegion,
        startingLocation = run.startingLocation or {},
        current = Identity.observeCharacter(player),
        selectedStartingTraits = copyList(run.selectedStartingTraits),
        selectedStartingTraitsPartial = run.selectedStartingTraitsPartial == true,
        selectedStartingTraitsCapturedUtc =
            math.max(0, math.floor(tonumber(run.selectedStartingTraitsCapturedUtc) or 0)),
        startingEffectiveTraits = copyList(run.startingEffectiveTraits),
        currentEffectiveTraits = Identity.observeTraits(player),
    }
end

local function verifyReadback(decoded, ledger, projection)
    if type(decoded.projection) ~= "table" then
        return false, "export_readback_mismatch:projection:missing"
    end
    local actual = decoded.projection
    local actualWeaponKills = actual.weaponKills or {}
    local projectedWeaponKills = projection.weaponKills or {}
    local actualFireDeaths = actual.fireDeaths or {}
    local projectedFireDeaths = projection.fireDeaths or {}
    local actualKillTypes = actual.zombieKillTypes or {}
    local projectedKillTypes = projection.zombieKillTypes or {}
    if type(actual.challenge) ~= "table" then
        return false, "export_readback_mismatch:challenge:missing"
    end
    if type(actual.activeDay) ~= "table" then
        return false, "export_readback_mismatch:activeDay:missing"
    end
    if #decoded.bodies ~= #ledger.records then
        return false, "export_readback_mismatch:eventBodies:count"
    end
    for index, record in ipairs(ledger.records) do
        if decoded.bodies[index] ~= record.body then
            return false, "export_readback_mismatch:eventBodies:"
                .. tostring(index)
        end
    end

    local function count(values)
        return type(values) == "table" and #values or -1
    end
    local function check(field, observed, expected)
        if observed == expected then return nil end
        if type(observed) == "number" and type(expected) == "number" then
            local scale = math.max(1, math.abs(observed), math.abs(expected))
            if math.abs(observed - expected) <= scale * 1e-12 then
                return nil
            end
        end
        return "export_readback_mismatch:" .. field
            .. ":decoded=" .. tostring(observed)
            .. ":source=" .. tostring(expected)
    end

    local comparisons = {
        { "runId", decoded.runId, ledger.runId },
        { "eventSequence", decoded.eventSequence, ledger.eventSequence },
        { "eventHash", decoded.eventHash, ledger.eventHash },
        { "currentKills", decoded.currentKills, projection.currentKills },
        { "schema", actual.schema, projection.schema },
        { "lifecycle", actual.lifecycle, projection.lifecycle },
        { "endedReason", actual.endedReason, projection.endedReason },
        { "endedUtc", actual.endedUtc, projection.endedUtc },
        { "endedWorldAgeHours", actual.endedWorldAgeHours,
            projection.endedWorldAgeHours },
        { "endedEventSequence", actual.endedEventSequence,
            projection.endedEventSequence },
        { "recovery.schema", actual.recovery.schema,
            projection.recovery.schema },
        { "recovery.present", actual.recovery.present,
            projection.recovery.present },
        { "recovery.hasBranches", actual.recovery.hasBranches,
            projection.recovery.hasBranches },
        { "recovery.status", actual.recovery.status,
            projection.recovery.status },
        { "recovery.activeEpoch", actual.recovery.activeEpoch,
            projection.recovery.activeEpoch },
        { "recovery.recoveries.count",
            count(actual.recovery.recoveries),
            count(projection.recovery.recoveries) },
        { "recovery.decisions.count",
            count(actual.recovery.decisions),
            count(projection.recovery.decisions) },
        { "challenge.id", actual.challenge.id, projection.challenge.id },
        { "challenge.gameMode", actual.challenge.gameMode,
            projection.challenge.gameMode },
        { "skills.count", count(actual.skills), count(projection.skills) },
        { "outposts.count", count(actual.outposts), count(projection.outposts) },
        { "activeMods.count", count(actual.activeMods),
            count(projection.activeMods) },
        { "activeDay.dayIndex", actual.activeDay.dayIndex,
            projection.activeDay.dayIndex },
        { "weight.currentKilograms", actual.weight.currentKilograms,
            projection.weight.currentKilograms },
        { "activeDay.weightDeltaKilograms",
            actual.activeDay.weightDeltaKilograms,
            projection.activeDay.weightDeltaKilograms },
        { "weaponKills.sources.count", count(actualWeaponKills.sources),
            count(projectedWeaponKills.sources) },
        { "fireDeaths.count", actualFireDeaths.count,
            projectedFireDeaths.count },
        { "zombieKillTypes.standing", actualKillTypes.standing,
            projectedKillTypes.standing },
        { "zombieKillTypes.onfront", actualKillTypes.onfront,
            projectedKillTypes.onfront },
        { "zombieKillTypes.onback", actualKillTypes.onback,
            projectedKillTypes.onback },
        { "zombieKillTypes.fenceAssist",
            actualKillTypes.fenceAssist,
            projectedKillTypes.fenceAssist },
        { "zombieKillTypes.windowAssist",
            actualKillTypes.windowAssist,
            projectedKillTypes.windowAssist },
        { "townVisits.towns.count", count(actual.townVisits.towns),
            count(projection.townVisits.towns) },
        { "literature.currentItemIds.count",
            count(actual.literature.currentItemIds),
            count(projection.literature.currentItemIds) },
        { "locations.entries.count", count(actual.locations.entries),
            count(projection.locations.entries) },
        { "milestones.outpostCompletions.count",
            count(actual.milestones.outpostCompletions),
            count(projection.milestones.outpostCompletions) },
        { "milestones.killMilestones.count",
            count(actual.milestones.killMilestones),
            count(projection.milestones.killMilestones) },
        { "milestones.skillMilestones.count",
            count(actual.milestones.skillMilestones),
            count(projection.milestones.skillMilestones) },
        { "milestones.outpostDeliverableMilestones.count",
            count(actual.milestones.outpostDeliverableMilestones),
            count(projection.milestones.outpostDeliverableMilestones) },
        { "distance.travelledMeters", actual.distance.travelledMeters,
            projection.distance.travelledMeters },
        { "activeDay.distanceDeltaMeters",
            actual.activeDay.distanceDeltaMeters,
            projection.activeDay.distanceDeltaMeters },
        { "nimbleStance.movementMilliseconds",
            actual.nimbleStance.movementMilliseconds,
            projection.nimbleStance.movementMilliseconds },
        { "activeGameplay.milliseconds",
            actual.activeGameplay.milliseconds,
            projection.activeGameplay.milliseconds },
        { "brokenWeapons.total", actual.brokenWeapons.total,
            projection.brokenWeapons.total },
        { "brokenWeapons.weapons.count",
            count(actual.brokenWeapons.weapons),
            count(projection.brokenWeapons.weapons) },
        { "animalsSlaughtered.total", actual.animalsSlaughtered.total,
            projection.animalsSlaughtered.total },
        { "animalsSlaughtered.animalTypes.count",
            count(actual.animalsSlaughtered.animalTypes),
            count(projection.animalsSlaughtered.animalTypes) },
        { "animalsTrapped.total", actual.animalsTrapped.total,
            projection.animalsTrapped.total },
        { "animalsTrapped.animalTypes.count",
            count(actual.animalsTrapped.animalTypes),
            count(projection.animalsTrapped.animalTypes) },
        { "animalsTrapped.traps.count", count(actual.animalsTrapped.traps),
            count(projection.animalsTrapped.traps) },
        { "animalsTrapped.pairs.count", count(actual.animalsTrapped.pairs),
            count(projection.animalsTrapped.pairs) },
        { "activeDay.animalTrapDeltas.count",
            count(actual.activeDay.animalTrapDeltas),
            count(projection.activeDay.animalTrapDeltas) },
        { "animalBirths.total", actual.animalBirths.total,
            projection.animalBirths.total },
        { "animalBirths.animalTypes.count",
            count(actual.animalBirths.animalTypes),
            count(projection.animalBirths.animalTypes) },
        { "animalsPetted.total", actual.animalsPetted.total,
            projection.animalsPetted.total },
        { "animalsPetted.animalTypes.count",
            count(actual.animalsPetted.animalTypes),
            count(projection.animalsPetted.animalTypes) },
        { "activeDay.animalBirthDeltas.count",
            count(actual.activeDay.animalBirthDeltas),
            count(projection.activeDay.animalBirthDeltas) },
        { "milkCollected.total", actual.milkCollected.total,
            projection.milkCollected.total },
        { "milkCollected.milkTypes.count",
            count(actual.milkCollected.milkTypes),
            count(projection.milkCollected.milkTypes) },
        { "activeDay.milkCollectedDeltas.count",
            count(actual.activeDay.milkCollectedDeltas),
            count(projection.activeDay.milkCollectedDeltas) },
        { "fluidConsumed.totalLiters",
            actual.fluidConsumed.totalLiters,
            projection.fluidConsumed.totalLiters },
        { "fluidConsumed.fluidTypes.count",
            count(actual.fluidConsumed.fluidTypes),
            count(projection.fluidConsumed.fluidTypes) },
        { "caloriesConsumed.totalKilocalories",
            actual.caloriesConsumed.totalKilocalories,
            projection.caloriesConsumed.totalKilocalories },
        { "butterProduced.count", actual.butterProduced.count,
            projection.butterProduced.count },
        { "activeDay.butterProducedDelta",
            actual.activeDay.butterProducedDelta,
            projection.activeDay.butterProducedDelta },
        { "fishCaught.total", actual.fishCaught.total,
            projection.fishCaught.total },
        { "fishCaught.fish.count", count(actual.fishCaught.fish),
            count(projection.fishCaught.fish) },
        { "activeDay.fishCaughtDeltas.count",
            count(actual.activeDay.fishCaughtDeltas),
            count(projection.activeDay.fishCaughtDeltas) },
        { "generatorKnowledge.known", actual.generatorKnowledge.known,
            projection.generatorKnowledge.known },
        { "generatorKnowledge.recipeId", actual.generatorKnowledge.recipeId,
            projection.generatorKnowledge.recipeId },
        { "generatorRepairs.count", actual.generatorRepairs.count,
            projection.generatorRepairs.count },
        { "generatorRepairs.conditionRestored",
            actual.generatorRepairs.conditionRestored,
            projection.generatorRepairs.conditionRestored },
        { "injuries.all.total", actual.injuries.all.total,
            projection.injuries.all.total },
        { "injuries.all.pairs.count", count(actual.injuries.all.pairs),
            count(projection.injuries.all.pairs) },
        { "injuries.zombieAssociated.total",
            actual.injuries.zombieAssociated.total,
            projection.injuries.zombieAssociated.total },
        { "activeDay.injuryDeltas.count",
            count(actual.activeDay.injuryDeltas),
            count(projection.activeDay.injuryDeltas) },
        { "activeDay.zombieAssociatedInjuryDeltas.count",
            count(actual.activeDay.zombieAssociatedInjuryDeltas),
            count(projection.activeDay.zombieAssociatedInjuryDeltas) },
        { "challengeProgress.rulesVersion",
            actual.challengeProgress.rulesVersion,
            projection.challengeProgress.rulesVersion },
    }
    for _, comparison in ipairs(comparisons) do
        local reason = check(
            comparison[1], comparison[2], comparison[3])
        if reason then return false, reason end
    end
    return true
end

function Exporter.generate(run, work, options)
    options = options or {}
    local timings = {}
    local stageStarted = milliseconds()
    local function finishStage(name)
        local now = milliseconds()
        timings[name] = now - stageStarted
        stageStarted = now
    end
    if not run then
        local identityError
        run, identityError = Identity.get()
        if not run then
            return false, identityError or "missing_active_run"
        end
    end
    if not run.runId then return false, "missing_active_run" end
    if work then work("prepare", 0, 1) end
    if not codecSelfTestPassed then
        local codecOk, codecError = ExportCodec.selfTest(function(_, current, total)
            if work then work("prepare", current, total) end
        end)
        if not codecOk then return false, codecError end
        codecSelfTestPassed = true
    end
    finishStage("selfTest")

    local ledger, ledgerError = options.ledger, nil
    if not ledger then
        ledger, ledgerError = Ledger.readAll(run, function(_, current, total)
            if work then work("verify_ledger", current, total) end
        end)
    end
    if not ledger then return false, ledgerError end
    finishStage("ledger")
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    if work then work("build_projection", 0, 1) end
    local recovery, recoveryError =
        Ledger.recoveryEvidence(run, work, ledger.records)
    if not recovery then return false, recoveryError end
    local milestones, milestoneError =
        MilestoneSnapshot.observe(run, ledger.records)
    if not milestones then return false, milestoneError end
    local outpostLifecycles, lifecycleError =
        OutpostLifecycleSnapshot.observe(run, ledger.records)
    if not outpostLifecycles then return false, lifecycleError end
    finishStage("evidence")
    local projection = {
        schema = 2,
        lifecycle = tostring(run.lifecycle or "active"),
        endedReason = run.endedReason,
        endedUtc = run.endedUtc,
        endedWorldAgeHours = run.endedWorldAgeHours,
        endedEventSequence = run.endedEventSequence,
        recovery = recovery,
        challenge = Identity.exportChallenge(run),
        currentKills = math.max(0, tonumber(player and player:getZombieKills()) or 0),
        character = characterProjection(run, player),
        skills = SkillSnapshot.observe(player),
        outposts = OutpostSnapshot.observe(outpostLifecycles),
        challengeProgress = ChallengeProgressSnapshot.observe(player),
        activeMods = ModSnapshot.observe(),
        activeDay = DailySnapshot.active(run, player),
        weight = {
            unit = "kilogram",
            currentKilograms = DailySnapshot.current(
                player, run).weightKilograms,
        },
        weaponKills = {
            partial = run.weaponKillsPartial == true,
            baselineTotal = math.max(0,
                math.floor(tonumber(run.weaponKillsBaselineTotal) or 0)),
            sources = WeaponKillSnapshot.list(run.weaponKills),
        },
        fireDeaths = {
            count = math.max(0, math.floor(tonumber(run.fireDeaths) or 0)),
            partial = run.fireDeathsPartial == true,
        },
        zombieKillTypes = {
            standing = math.max(0, math.floor(tonumber(
                run.zombieKillTypes and
                run.zombieKillTypes.standing) or 0)),
            onfront = math.max(0, math.floor(tonumber(
                run.zombieKillTypes and
                run.zombieKillTypes.onfront) or 0)),
            onback = math.max(0, math.floor(tonumber(
                run.zombieKillTypes and
                run.zombieKillTypes.onback) or 0)),
            fenceAssist = math.max(0, math.floor(tonumber(
                run.zombieKillTypes and
                run.zombieKillTypes.fenceAssist) or 0)),
            windowAssist = math.max(0, math.floor(tonumber(
                run.zombieKillTypes and
                run.zombieKillTypes.windowAssist) or 0)),
            partial = run.zombieKillTypesPartial == true,
        },
        townVisits = TownSnapshot.observe(run),
        literature = LiteratureSnapshot.observe(run),
        locations = LocationSnapshot.observe(run),
        milestones = milestones,
        distance = {
            unit = "meter",
            travelledMeters = math.max(0,
                tonumber(run.distanceTravelledMeters) or 0),
            rejectedSamples = math.max(0, math.floor(
                tonumber(run.distanceRejectedSamples) or 0)),
            partial = run.distanceTravelledPartial == true,
        },
        nimbleStance = {
            unit = "millisecond",
            movementMilliseconds = math.max(0,
                tonumber(run.nimbleStanceMovementMilliseconds) or 0),
            partial = run.nimbleStanceMovementPartial == true,
        },
        activeGameplay = {
            unit = "millisecond",
            milliseconds = math.max(0,
                tonumber(run.activeGameplayMilliseconds) or 0),
            partial = run.activeGameplayPartial == true,
        },
        brokenWeapons = {
            total = math.max(0, math.floor(
                tonumber(run.brokenWeaponsTotal) or 0)),
            partial = run.brokenWeaponsPartial == true,
            weapons = BrokenWeaponSnapshot.list(run.brokenWeapons),
        },
        animalsSlaughtered = {
            total = math.max(0, math.floor(
                tonumber(run.animalsSlaughteredTotal) or 0)),
            partial = run.animalsSlaughteredPartial == true,
            animalTypes =
                AnimalSlaughterSnapshot.list(run.animalsSlaughtered),
        },
        animalsTrapped = {
            total = math.max(0, math.floor(
                tonumber(run.animalsTrappedTotal) or 0)),
            partial = run.animalsTrappedPartial == true,
            animalTypes =
                AnimalTrapSnapshot.animalTypes(run.animalsTrapped),
            traps = AnimalTrapSnapshot.traps(run.animalsTrapped),
            pairs = AnimalTrapSnapshot.pairs(run.animalsTrapped),
        },
        animalBirths = {
            total = math.max(0, math.floor(
                tonumber(run.animalBirthsTotal) or 0)),
            partial = run.animalBirthsPartial == true,
            animalTypes = AnimalBirthSnapshot.list(run.animalBirths),
        },
        animalsPetted = {
            total = math.max(0, math.floor(
                tonumber(run.animalsPettedTotal) or 0)),
            partial = run.animalsPettedPartial == true,
            animalTypes = AnimalPetSnapshot.list(run.animalsPetted),
        },
        milkCollected = {
            unit = "liter",
            total = math.max(0, tonumber(run.milkCollectedTotal) or 0),
            partial = run.milkCollectedPartial == true,
            milkTypes = MilkSnapshot.list(run.milkCollected),
        },
        fluidConsumed = {
            unit = "liter",
            totalLiters =
                math.max(0, tonumber(run.fluidConsumedTotal) or 0),
            partial = run.fluidConsumedPartial == true,
            fluidTypes =
                FluidConsumedSnapshot.list(run.fluidConsumed),
        },
        caloriesConsumed = {
            unit = "kilocalorie",
            totalKilocalories =
                math.max(0, tonumber(run.caloriesConsumed) or 0),
            partial = run.caloriesConsumedPartial == true,
        },
        butterProduced = {
            itemId = "Base.Butter",
            count = math.max(0,
                math.floor(tonumber(run.butterProduced) or 0)),
            partial = run.butterProducedPartial == true,
        },
        fishCaught = {
            total = math.max(0,
                math.floor(tonumber(run.fishCaughtTotal) or 0)),
            partial = run.fishCaughtPartial == true,
            fish = FishCaughtSnapshot.list(run.fishCaught),
        },
        generatorKnowledge = GeneratorKnowledgeSnapshot.observe(run),
        generatorRepairs = {
            count = math.max(0, math.floor(
                tonumber(run.generatorRepairs) or 0)),
            conditionRestored = math.max(0,
                tonumber(run.generatorConditionRestored) or 0),
            partial = run.generatorRepairsPartial == true,
        },
        injuries = {
            partial = run.injuriesPartial == true,
            all = InjurySnapshot.observe(
                run.injuries, run.injuriesTotal),
            zombieAssociated = InjurySnapshot.observe(
                run.zombieAssociatedInjuries,
                run.zombieAssociatedInjuriesTotal),
        },
    }
    if not projection.activeDay then return false, "missing_active_day" end
    omitFalsePartialFlags(projection)
    omitEmptyKillEvidence(projection)
    finishStage("projection")
    local encoded, stats = ExportCodec.encode(
        ledger.runId,
        Identity.utcSeconds(),
        ledger.records,
        ledger.eventHash,
        projection,
        work
    )
    finishStage("encode")
    local decoded, decodeError = ExportCodec.decode(encoded, work, {
        verifyLedger = false,
    })
    if not decoded then return false, decodeError end
    finishStage("decode")
    if work then work("compare_readback", 0, 1) end
    local verified, verifyError =
        verifyReadback(decoded, ledger, projection)
    if not verified then return false, verifyError end
    finishStage("readback")

    local filename = options.filename
        or ROOT .. "/" .. ledger.runId .. "/run.export.txt"
    if work then work("write", 0, 1) end
    local writer = getFileWriter(filename, true, false)
    if not writer then return false, "unable_to_write_export" end
    writer:write(encoded)
    writer:close()
    finishStage("write")
    stats.eventSequence = ledger.eventSequence
    stats.eventHash = ledger.eventHash
    stats.currentKills = projection.currentKills
    stats.projection = projection
    stats.filename = filename
    stats.value = encoded
    stats.syntheticDays = options.syntheticDays
    stats.syntheticBuildMilliseconds = options.syntheticBuildMilliseconds
    stats.exportMilliseconds = options.exportStartedMilliseconds
        and milliseconds() - options.exportStartedMilliseconds or nil
    stats.profileMilliseconds = timings
    return true, stats
end

function Exporter.begin(run, options)
    local job = {
        done = false,
        phase = "prepare",
        progress = 0,
    }
    local function work(phase, current, total)
        job.phase = phase or job.phase
        job.progress = total and total > 0 and math.min(1, current / total) or 0
        if milliseconds() - job.sliceStarted >= SLICE_MILLISECONDS then coroutine.yield() end
    end
    job.thread = coroutine.create(function()
        local ok, result = Exporter.generate(run, work, options)
        job.ok, job.result, job.done = ok, result, true
    end)
    return job
end

function Exporter.step(job)
    if not job or job.done then return job and job.ok, job and job.result end
    if job.stepping then return nil, nil end
    job.stepping = true
    job.sliceStarted = milliseconds()
    local resumed, errorMessage = coroutine.resume(job.thread)
    job.stepping = false
    if not resumed then
        job.ok, job.result, job.done = false, tostring(errorMessage), true
    elseif coroutine.status(job.thread) == "dead" and not job.done then
        job.ok, job.result, job.done = false, "export_job_ended_without_result", true
    end
    return job.done and job.ok or nil, job.done and job.result or nil
end

return Exporter
