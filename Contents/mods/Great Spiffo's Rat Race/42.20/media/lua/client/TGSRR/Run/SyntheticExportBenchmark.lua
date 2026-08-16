local Identity = require "TGSRR/Run/Identity"
local EventCodec = require "TGSRR/Run/EventCodec"
local Exporter = require "TGSRR/Run/Exporter"

local Benchmark = {}
local historyCaches = {}
local BENCHMARK_BASE_UTC = 1700000000

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

local function copyRun(run)
    local result = {}
    for key, value in pairs(run or {}) do result[key] = value end
    return result
end

local function completedDay(dayIndex, startedUtc, startedWorldAgeHours)
    local result = {
        dayIndex = dayIndex,
        startedUtc = startedUtc,
        startedWorldAgeHours = startedWorldAgeHours,
        killDelta = 35 + dayIndex % 31,
        weightDeltaKilograms = ((dayIndex % 9) - 4) / 100,
        xpDeltas = {
            Fitness = 8 + dayIndex % 7,
            Sprinting = 12 + dayIndex % 13,
            Maintenance = 5 + dayIndex % 11,
        },
        weaponKillDeltas = {
            ["Base.Axe"] = 12 + dayIndex % 9,
            ["Base.KitchenKnife"] = 3 + dayIndex % 5,
        },
        distanceDeltaMeters = 1800 + dayIndex % 1200,
    }
    if dayIndex % 5 == 0 then
        result.brokenWeaponDeltas = { ["Base.KitchenKnife"] = 1 }
    end
    if dayIndex % 3 == 0 then
        result.fishCaughtDeltas = { ["Base.Pike"] = 1 }
    end
    if dayIndex % 7 == 0 then result.butterProducedDelta = 1 end
    return result
end

function Benchmark.begin(days)
    days = math.max(1, math.floor(tonumber(days) or 3650))
    local run, runError = Identity.get()
    if not run then return nil, runError or "missing_active_run" end

    local started = milliseconds()
    local cache = historyCaches[run.runId]
    if not cache then
        cache = {
            records = {},
            cumulativeKills = {},
            builtDays = 0,
        }
        historyCaches[run.runId] = cache
    end
    local syntheticRun = copyRun(run)

    local function build(work)
        local previousHash = cache.builtDays > 0
            and cache.records[cache.builtDays].hash
            or EventCodec.GENESIS_HASH
        for offset = cache.builtDays + 1, days do
            local dayIndex = offset
            local startedUtc = BENCHMARK_BASE_UTC + (offset - 1) * 86400
            local startedWorldAgeHours = (offset - 1) * 24
            local sequence = offset
            local completed = completedDay(
                dayIndex, startedUtc, startedWorldAgeHours)
            local record, recordError = EventCodec.encode({
                runId = run.runId,
                epoch = 1,
                sequence = sequence,
                utc = BENCHMARK_BASE_UTC + offset * 86400,
                worldAgeHours = offset * 24,
                eventType = "day.started",
                payload = {
                    dayIndex = dayIndex + 1,
                    completedDay = completed,
                },
            }, previousHash, function()
                work("synthetic_history", offset, days)
            end)
            if not record then return false, recordError end
            cache.records[offset] = record
            cache.cumulativeKills[offset] =
                (cache.cumulativeKills[offset - 1] or 0)
                + completed.killDelta
            previousHash = record.hash
        end
        cache.builtDays = math.max(cache.builtDays, days)

        local sequence = days
        local eventHash = days > 0 and cache.records[sequence].hash
            or EventCodec.GENESIS_HASH
        local records = {}
        for index = 1, sequence do records[index] = cache.records[index] end
        syntheticRun.eventSequence = sequence
        syntheticRun.eventHash = eventHash
        local buildMilliseconds = milliseconds() - started
        return Exporter.generate(syntheticRun, work, {
            ledger = {
                runId = run.runId,
                eventSequence = sequence,
                eventHash = eventHash,
                records = records,
            },
            filename = "TGSRR/Runs/" .. run.runId
                .. "/synthetic-" .. tostring(days) .. "-day.export.txt",
            syntheticDays = days,
            syntheticCurrentKills = cache.cumulativeKills[days] or 0,
            syntheticBuildMilliseconds = buildMilliseconds,
            exportStartedMilliseconds = milliseconds(),
        })
    end

    local job = {
        done = false,
        phase = "synthetic_days",
        progress = 0,
    }
    local function work(phase, current, total)
        job.phase = phase or job.phase
        job.progress = total and total > 0
            and math.min(1, current / total) or 0
        if milliseconds() - job.sliceStarted >= 8 then coroutine.yield() end
    end
    job.thread = coroutine.create(function()
        local ok, result = build(work)
        job.ok, job.result, job.done = ok, result, true
    end)
    return job
end

return Benchmark
