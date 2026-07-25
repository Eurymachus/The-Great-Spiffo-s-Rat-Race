local Identity = require "TGSRR/Run/Identity"
local Ledger = require "TGSRR/Run/Ledger"
local ExportCodec = require "TGSRR/Run/ExportCodec"
local SkillSnapshot = require "TGSRR/Run/SkillSnapshot"
local OutpostSnapshot = require "TGSRR/Run/OutpostSnapshot"
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

local Exporter = {}

local ROOT = "TGSRR/Runs"
local SLICE_MILLISECONDS = 8

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function copyList(values)
    local result = {}
    for index, value in ipairs(values or {}) do result[index] = tostring(value) end
    return result
end

local function characterProjection(run, player)
    return {
        starting = run.startingCharacter or {},
        current = Identity.observeCharacter(player),
        selectedStartingTraits = copyList(run.selectedStartingTraits),
        selectedStartingTraitsPartial = run.selectedStartingTraitsPartial == true,
        selectedStartingTraitsCapturedUtc =
            math.max(0, math.floor(tonumber(run.selectedStartingTraitsCapturedUtc) or 0)),
        startingEffectiveTraits = copyList(run.startingEffectiveTraits),
        currentEffectiveTraits = Identity.observeTraits(player),
    }
end

function Exporter.generate(run, work)
    run = run or Identity.get()
    if not run or not run.runId then return false, "missing_active_run" end
    local codecOk, codecError = ExportCodec.selfTest(work)
    if not codecOk then return false, codecError end

    local ledger, ledgerError = Ledger.readAll(run, work)
    if not ledger then return false, ledgerError end
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    local milestones, milestoneError =
        MilestoneSnapshot.observe(run, ledger.records)
    if not milestones then return false, milestoneError end
    local projection = {
        schema = 1,
        challenge = Identity.exportChallenge(run),
        currentKills = math.max(0, tonumber(player and player:getZombieKills()) or 0),
        character = characterProjection(run, player),
        skills = SkillSnapshot.observe(player),
        outposts = OutpostSnapshot.observe(),
        challengeProgress = ChallengeProgressSnapshot.observe(player),
        activeMods = ModSnapshot.observe(),
        activeDay = DailySnapshot.active(run, player),
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
    }
    if not projection.activeDay then return false, "missing_active_day" end
    local encoded, stats = ExportCodec.encode(
        ledger.runId,
        Identity.utcSeconds(),
        ledger.records,
        ledger.eventHash,
        projection,
        work
    )
    local decoded, decodeError = ExportCodec.decode(encoded, work)
    if not decoded then return false, decodeError end
    if decoded.runId ~= ledger.runId or decoded.eventSequence ~= ledger.eventSequence
            or decoded.eventHash ~= ledger.eventHash
            or decoded.currentKills ~= projection.currentKills
            or not decoded.projection or decoded.projection.schema ~= projection.schema
            or not decoded.projection.challenge
            or decoded.projection.challenge.id ~= projection.challenge.id
            or decoded.projection.challenge.gameMode ~= projection.challenge.gameMode
            or #decoded.projection.skills ~= #projection.skills
            or #decoded.projection.outposts ~= #projection.outposts
            or #decoded.projection.activeMods ~= #projection.activeMods
            or not decoded.projection.activeDay
            or decoded.projection.activeDay.dayIndex ~= projection.activeDay.dayIndex
            or #decoded.projection.weaponKills.sources ~=
                #projection.weaponKills.sources
            or decoded.projection.fireDeaths.count ~=
                projection.fireDeaths.count
            or #decoded.projection.townVisits.towns ~=
                #projection.townVisits.towns
            or #decoded.projection.literature.currentItemIds ~=
                #projection.literature.currentItemIds
            or #decoded.projection.locations.entries ~=
                #projection.locations.entries
            or #decoded.projection.milestones.outpostCompletions ~=
                #projection.milestones.outpostCompletions
            or #decoded.projection.milestones.killMilestones ~=
                #projection.milestones.killMilestones
            or #decoded.projection.milestones.outpostDeliverableMilestones ~=
                #projection.milestones.outpostDeliverableMilestones
            or decoded.projection.distance.travelledMeters ~=
                projection.distance.travelledMeters
            or decoded.projection.activeDay.distanceDeltaMeters ~=
                projection.activeDay.distanceDeltaMeters
            or decoded.projection.brokenWeapons.total ~=
                projection.brokenWeapons.total
            or #decoded.projection.brokenWeapons.weapons ~=
                #projection.brokenWeapons.weapons
            or decoded.projection.animalsSlaughtered.total ~=
                projection.animalsSlaughtered.total
            or #decoded.projection.animalsSlaughtered.animalTypes ~=
                #projection.animalsSlaughtered.animalTypes
            or decoded.projection.animalsTrapped.total ~=
                projection.animalsTrapped.total
            or #decoded.projection.animalsTrapped.animalTypes ~=
                #projection.animalsTrapped.animalTypes
            or #decoded.projection.animalsTrapped.traps ~=
                #projection.animalsTrapped.traps
            or #decoded.projection.animalsTrapped.pairs ~=
                #projection.animalsTrapped.pairs
            or #decoded.projection.activeDay.animalTrapDeltas ~=
                #projection.activeDay.animalTrapDeltas
            or decoded.projection.animalBirths.total ~=
                projection.animalBirths.total
            or #decoded.projection.animalBirths.animalTypes ~=
                #projection.animalBirths.animalTypes
            or #decoded.projection.activeDay.animalBirthDeltas ~=
                #projection.activeDay.animalBirthDeltas
            or decoded.projection.challengeProgress.rulesVersion ~=
                projection.challengeProgress.rulesVersion then
        return false, "export_readback_mismatch"
    end

    local filename = ROOT .. "/" .. ledger.runId .. "/run.export"
    local writer = getFileWriter(filename, true, false)
    if not writer then return false, "unable_to_write_export" end
    writer:write(encoded)
    writer:close()
    stats.eventSequence = ledger.eventSequence
    stats.eventHash = ledger.eventHash
    stats.currentKills = projection.currentKills
    stats.projection = projection
    stats.filename = filename
    stats.value = encoded
    return true, stats
end

function Exporter.begin(run)
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
        local ok, result = Exporter.generate(run, work)
        job.ok, job.result, job.done = ok, result, true
    end)
    return job
end

function Exporter.step(job)
    if not job or job.done then return job and job.ok, job and job.result end
    job.sliceStarted = milliseconds()
    local resumed, errorMessage = coroutine.resume(job.thread)
    if not resumed then
        job.ok, job.result, job.done = false, tostring(errorMessage), true
    elseif coroutine.status(job.thread) == "dead" and not job.done then
        job.ok, job.result, job.done = false, "export_job_ended_without_result", true
    end
    return job.done and job.ok or nil, job.done and job.result or nil
end

return Exporter
