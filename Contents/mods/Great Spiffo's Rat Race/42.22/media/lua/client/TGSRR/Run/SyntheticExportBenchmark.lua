local Identity = require("TGSRR/Run/Identity")
local EventCodec = require("TGSRR/Run/EventCodec")
local Exporter = require("TGSRR/Run/Exporter")
local Ledger = require("TGSRR/Run/Ledger")

local Benchmark = {}
local FIXTURE_VERSION = 2
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

local function syntheticCalendar(dayIndex)
    local year, month, day = 1993, 1, dayIndex
    local lengths = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}
    while true do
        local length = lengths[month]
        if month == 2 and year % 4 == 0
                and (year % 100 ~= 0 or year % 400 == 0) then length = 29 end
        if day <= length then break end
        day = day - length
        month = month + 1
        if month > 12 then month, year = 1, year + 1 end
    end
    return { year = year, month = month, day = day }
end

local function completedDay(dayIndex, startedUtc, startedWorldAgeHours)
    local result = {
        dayIndex = dayIndex,
        startedUtc = startedUtc,
        startedWorldAgeHours = startedWorldAgeHours,
        killDelta = 35 + dayIndex % 31,
        weightDeltaKilograms = ((dayIndex % 9) - 4) / 100,
        weightKilograms = 80 + ((dayIndex % 9) - 4) / 100,
        outdoorTemperature = {
            schema = 1,
            unit = "celsius",
            source = "outdoor_weather",
            sampleIntervalGameMinutes = 1,
            minimum = {
                celsius = -15 + dayIndex % 35,
                utc = startedUtc + 21600,
                worldAgeHours = startedWorldAgeHours + 6,
                timeOfDay = 6,
                calendar = syntheticCalendar(dayIndex),
            },
            maximum = {
                celsius = -5 + dayIndex % 35,
                utc = startedUtc + 54000,
                worldAgeHours = startedWorldAgeHours + 15,
                timeOfDay = 15,
                calendar = syntheticCalendar(dayIndex),
            },
        },
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
        distanceByModeDeltas = { onFoot = 800 + dayIndex % 1200, driver = 1000 },
        fireDeathDelta = 1,
        animalSlaughterDeltas = { cow = 1, chicken = 2 },
        animalTrapDeltas = {
            { animalType = "rabbit", trapId = "Base.TrapBox", trapped = 1 },
        },
        animalBirthDeltas = { cow = 1, chicken = 2 },
        animalPetDeltas = { cow = 2, sheep = 1 },
        milkCollectedDeltas = { Milk = 1.5, SheepMilk = 0.5 },
        entertainmentLiteratureDeltas = { ["Base.Book_Art"] = 1, ["Base.Paperback_Art"] = 1 },
        injuryDeltas = {
            { injuryType = "scratch", bodyPart = "Hand_L", count = 2 },
        },
        zombieAssociatedInjuryDeltas = {
            { injuryType = "scratch", bodyPart = "Hand_L", count = 1 },
        },
        fluidConsumedDeltas = { Water = 2, Milk = 0.25 },
        caloriesConsumedDelta = 2500 + dayIndex % 500,
        generatorRepairDelta = 1,
        generatorConditionRestoredDelta = 4,
        nimbleMovementMillisecondsDelta = 60000,
        activeGameplayMillisecondsDelta = 3600000,
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

-- Each fixture occupies its own deterministic directory. Regeneration overwrites
-- only that fixture, while stable records permit repeat-export cache measurements.
local function writeFixture(run, days, work)
    local previousHash = EventCodec.GENESIS_HASH
    local kills, bytes = 0, 0
    local writer
    for day = 1, days do
        local startedUtc = BENCHMARK_BASE_UTC + (day - 1) * 86400
        local completed = completedDay(day, startedUtc, (day - 1) * 24)
        kills = kills + completed.killDelta
        local record, err = EventCodec.encode({
            runId = run.runId, epoch = 1, sequence = day,
            utc = startedUtc + 86400, worldAgeHours = day * 24,
            eventType = "day.started",
            payload = { dayIndex = day + 1, completedDay = completed },
        }, previousHash, work)
        if not record then
            if writer then writer:close() end
            return nil, err
        end
        local position = (day - 1) % Ledger.eventsPerSegment + 1
        if position == 1 then
            local index = math.floor((day - 1) / Ledger.eventsPerSegment) + 1
            local filename = "TGSRR/Runs/" .. run.runId .. "/segments/events-"
                .. string.format("%06d", index) .. ".log"
            writer = getFileWriter(filename, true, false)
            if not writer then return nil, "unable_to_write_benchmark_segment" end
            local header = table.concat({ "H", Ledger.segmentFormat, index, day, previousHash }, "|") .. "\n"
            writer:write(header)
            bytes = bytes + #header
        end
        local encoded = record.body:gsub(".", function(c)
            return string.format("%02x", string.byte(c))
        end)
        local line = table.concat({ "R", day, previousHash, record.hash, #record.body, encoded }, "|") .. "\n"
        writer:write(line)
        bytes = bytes + #line
        if position == Ledger.eventsPerSegment then
            local seal = table.concat({ "S", position, day, record.hash }, "|") .. "\n"
            writer:write(seal)
            bytes = bytes + #seal
        end
        if position == Ledger.eventsPerSegment or day == days then
            writer:close()
            writer = nil
        end
        previousHash = record.hash
        work("synthetic_history", day, days)
    end
    run.eventSequence, run.eventHash = days, previousHash
    return { kills = kills, bytes = bytes }
end

function Benchmark.begin(days)
    days = tonumber(days)
    if not days or days ~= math.floor(days) or days < 1 or days > 3650 then
        return nil, "benchmark_days_out_of_range"
    end
    local run, runError = Identity.get()
    if not run then return nil, runError or "missing_active_run" end
    local syntheticRun = copyRun(run)
    syntheticRun.runId = run.runId .. "-benchmark-v" .. FIXTURE_VERSION .. "-" .. days
    syntheticRun.epoch = 1
    syntheticRun.branchCheckpointSequence = nil
    syntheticRun.branchCheckpointHash = nil
    syntheticRun.dailyState = nil
    local memory = { source = "sampled_jvm_heap", samples = 0 }
    local stage = "build"
    local lastSample = -1
    local function sample(force)
        local now = milliseconds()
        if not force and now - lastSample < 10 then return end
        lastSample = now
        -- Build 26486631 BaseLib exposes used/free/committed JVM heap in KiB.
        -- This is whole-JVM sampled usage, not exact peak or process RSS.
        local used = collectgarbage("count")
        memory.samples = memory.samples + 1
        local baseline = stage .. "BaselineKiB"
        local peak = stage .. "PeakKiB"
        memory[baseline] = memory[baseline] or used
        memory[peak] = math.max(memory[peak] or used, used)
        memory[stage .. "EndKiB"] = used
    end
    local job = { done = false, phase = "synthetic_days", progress = 0 }
    local function work(phase, current, total)
        sample(false)
        job.phase = phase or job.phase
        job.progress = total and total > 0 and math.min(1, current / total) or 0
        if milliseconds() - job.sliceStarted >= 8 then coroutine.yield() end
    end
    job.thread = coroutine.create(function()
        sample(true)
        local started = milliseconds()
        local fixture, err = writeFixture(syntheticRun, days, work)
        sample(true)
        if not fixture then
            job.ok, job.result, job.done = false, err, true
            return
        end
        local buildMilliseconds = milliseconds() - started
        stage = "export"
        sample(true)
        -- No ledger override: use the same disk read/verification as a real export.
        local ok, result = Exporter.generate(syntheticRun, work, {
            filename = "TGSRR/Runs/" .. syntheticRun.runId
                .. "/synthetic-" .. days .. "-day.export.txt",
            syntheticDays = days,
            syntheticCurrentKills = fixture.kills,
            syntheticBuildMilliseconds = buildMilliseconds,
            exportStartedMilliseconds = milliseconds(),
        })
        sample(true)
        if ok then
            result.memory = memory
            result.syntheticLedgerBytes = fixture.bytes
            result.syntheticFixtureVersion = FIXTURE_VERSION
            result.syntheticDiskRead = true
            local reportPath = result.filename .. ".benchmark.txt"
            local report = getFileWriter(reportPath, true, false)
            if not report then
                job.ok, job.result, job.done = false, "unable_to_write_benchmark_report", true
                return
            end
            report:write("fixtureVersion=" .. FIXTURE_VERSION .. "\ndays=" .. days
                .. "\nledgerBytes=" .. fixture.bytes .. "\ndiskRead=true\n"
                .. "memoryScope=sampled whole-JVM heap, not process RSS or exact peak\n"
                .. "sampling=10ms minimum between cooperative work samples; stage boundaries always sampled\n"
                .. "diskCache=OS cache not cleared; fixture was just written\n")
            for key, value in pairs(memory) do report:write(key .. "=" .. tostring(value) .. "\n") end
            for _, key in ipairs({ "encodedCharacters", "syntheticBuildMilliseconds",
                    "exportMilliseconds", "reusedBlockCount", "builtBlockCount" }) do
                report:write(key .. "=" .. tostring(result[key]) .. "\n")
            end
            for key, value in pairs(result.profileMilliseconds or {}) do
                report:write("stageMilliseconds." .. key .. "=" .. value .. "\n")
            end
            report:close()
            result.benchmarkReportFilename = reportPath
        end
        job.ok, job.result, job.done = ok, result, true
    end)
    return job
end

return Benchmark
