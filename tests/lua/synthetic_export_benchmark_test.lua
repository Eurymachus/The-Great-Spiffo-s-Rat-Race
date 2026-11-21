local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. root .. "shared/?.lua;" .. package.path
local live = { runId = "rr-benchmark-test", epoch = 4, eventSequence = 77,
    eventHash = string.rep("a", 64), dailyState = { marker = "live" } }
package.loaded["TGSRR/Run/Identity"] = { get = function() return live end }

-- Real disk I/O behind PZ's file API. Temporary paths never touch game saves.
local paths, reads, writes = {}, 0, 0
local failWrite, corruptRead = false, false
getFileWriter = function(name, create, append)
    assert(name:match("^TGSRR/Runs/rr%-benchmark%-test%-benchmark%-v2%-%d+/"), name)
    if failWrite then return nil end
    if not paths[name] then paths[name] = os.tmpname() end
    local file = assert(io.open(paths[name], append and "ab" or "wb"))
    writes = writes + 1
    return { write = function(_, text) file:write(text) end,
        close = function() file:close() end }
end
getFileReader = function(name)
    assert(name:match("^TGSRR/Runs/rr%-benchmark%-test%-benchmark%-v2%-%d+/"), name)
    if not paths[name] then return nil end
    local file = assert(io.open(paths[name], "rb"))
    reads = reads + 1
    return { readLine = function()
            local line = file:read("*l")
            if corruptRead and line and line:sub(1, 2) == "R|" then return "corrupt" end
            return line
        end, close = function() file:close() end }
end
local now = 1000
getTimestampMs = function() now = now + 1; return now end
local originalGC = collectgarbage
local used = 100
collectgarbage = function(mode)
    assert(mode == "count", "benchmark must not force garbage collection")
    used = used + 10
    return used, 500, used + 500
end
local Ledger = require "TGSRR/Run/Ledger"
local EventCodec = require "TGSRR/Run/EventCodec"
local captured, capturedRun, capturedOptions
package.loaded["TGSRR/Run/Exporter"] = {
    generate = function(run, work, options)
        assert(options.ledger == nil, "must exercise production disk reader")
        assert(run.epoch == 1 and run.dailyState == nil)
        capturedRun, capturedOptions = run, options
        local ledger, err = Ledger.readAll(run, work)
        if not ledger then return false, err end
        captured = ledger
        return true, { filename = options.filename, syntheticDays = options.syntheticDays,
            eventSequence = ledger.eventSequence, profileMilliseconds = { ledger = 12 },
            syntheticBuildMilliseconds = options.syntheticBuildMilliseconds,
            exportMilliseconds = 20, encodedCharacters = 100, reusedBlockCount = 0, builtBlockCount = 1 }
    end,
}
local Benchmark = require "TGSRR/Run/SyntheticExportBenchmark"
local function run(days)
    local job = assert(Benchmark.begin(days))
    while not job.done do
        job.sliceStarted = getTimestampMs()
        local ok, err = coroutine.resume(job.thread)
        assert(ok, err)
    end
    return job
end
assert(Benchmark.begin(0) == nil)
assert(Benchmark.begin(3651) == nil)
assert(Benchmark.begin(1.5) == nil)
local job = run(7)
assert(job.ok, job.result)
assert(reads > 0 and writes > 0)
assert(job.result.syntheticDiskRead and job.result.syntheticLedgerBytes > 0)
assert(job.result.memory.exportPeakKiB >= job.result.memory.exportBaselineKiB)
assert(job.result.memory.buildPeakKiB >= job.result.memory.buildBaselineKiB)
assert(job.result.memory.samples > 4)
assert(paths[job.result.benchmarkReportFilename])
assert(live.epoch == 4 and live.eventSequence == 77 and live.dailyState.marker == "live")
local observed, previousHash = {}, EventCodec.GENESIS_HASH
for index, record in ipairs(captured.records) do
    assert(EventCodec.verify(record, previousHash))
    local inspected = assert(EventCodec.inspectBody(record.body))
    assert(inspected.sequence == index)
    local payload = assert(EventCodec.decodePayload(inspected.canonicalPayload))
    for key in pairs(payload.completedDay) do observed[key] = true end
    local day = payload.completedDay
    assert(day.distanceByModeDeltas.onFoot + day.distanceByModeDeltas.driver == day.distanceDeltaMeters)
    assert(day.zombieAssociatedInjuryDeltas[1].count <= day.injuryDeltas[1].count)
    previousHash = record.hash
end
-- Fail if a new daily metric is added without extending this fixture.
local tracker = assert(io.open(root .. "client/TGSRR/Run/DayTracker.lua", "rb"))
local source = tracker:read("*a"); tracker:close()
for key in source:gmatch('addDelta[s]?%(result, "([^"]+)"') do
    assert(observed[key], "missing synthetic daily metric: " .. key)
end
for key in source:gmatch('result%.([%w_]+Deltas)%s*=') do
    assert(observed[key], "missing synthetic daily metric: " .. key)
end
assert(observed.outdoorTemperature and observed.weightKilograms)
local hash = captured.eventHash
job = run(7)
assert(job.ok and captured.eventHash == hash, "repeat fixture must retain block identity")
local sevenId = capturedRun.runId
job = run(3)
assert(job.ok and capturedRun.runId ~= sevenId and #captured.records == 3)
-- Cross a real production segment boundary, including seal and final partial segment.
job = run(257)
assert(job.ok, job.result)
assert(#captured.records == 257)
corruptRead = true
job = run(1)
assert(not job.ok and job.result == "invalid_segment_frame:1", tostring(job.ok) .. ":" .. tostring(job.result))
corruptRead = false
failWrite = true
job = run(1)
assert(not job.ok and job.result == "unable_to_write_benchmark_segment")
for _, path in pairs(paths) do assert(os.remove(path)) end
collectgarbage = originalGC
print("synthetic benchmark: disk roundtrip, all daily fields, isolation, deterministic repeats, memory reporting and failure paths passed")
