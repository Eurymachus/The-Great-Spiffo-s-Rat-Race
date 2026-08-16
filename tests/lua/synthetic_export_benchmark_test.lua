local capturedOptions = nil

package.loaded["TGSRR/Run/Identity"] = {
    get = function()
        return {
            runId = "rr-benchmark-test",
            epoch = 4,
            eventSequence = 77,
            eventHash = string.rep("a", 64),
        }
    end,
    utcSeconds = function() return 1000 end,
}
package.loaded["TGSRR/Run/Ledger"] = {
    readAll = function()
        error("synthetic benchmark must not depend on the live ledger")
    end,
}
package.loaded["TGSRR/Run/Exporter"] = {
    generate = function(_, _, options)
        capturedOptions = options
        return true, {
            syntheticDays = options.syntheticDays,
            eventSequence = options.ledger.eventSequence,
        }
    end,
}

getTimestampMs = function() return 1000 end

local EventCodec = require "TGSRR/Run/EventCodec"
local originalEncode = EventCodec.encode
local encodeCalls = 0
EventCodec.encode = function(...)
    encodeCalls = encodeCalls + 1
    return originalEncode(...)
end
local Benchmark = require "TGSRR/Run/SyntheticExportBenchmark"
local job = assert(Benchmark.begin(3))
job.sliceStarted = 1000
while not job.done do
    local ok, errorMessage = coroutine.resume(job.thread)
    assert(ok, errorMessage)
end

assert(job.ok == true)
assert(job.result.syntheticDays == 3)
assert(job.result.eventSequence == 3)
assert(capturedOptions.filename:match("synthetic%-3%-day%.export%.txt$"))
assert(#capturedOptions.ledger.records == 3)
assert(encodeCalls == 3)

local previousHash = EventCodec.GENESIS_HASH
for index, record in ipairs(capturedOptions.ledger.records) do
    local verified, verifyError = EventCodec.verify(record, previousHash)
    assert(verified, verifyError)
    local inspected = assert(EventCodec.inspectBody(record.body))
    assert(inspected.sequence == index)
    assert(inspected.eventType == "day.started")
    local payload = assert(EventCodec.decodePayload(
        inspected.canonicalPayload))
    assert(payload.completedDay.killDelta > 0)
    assert(payload.completedDay.weightDeltaKilograms ~= nil)
    assert(payload.completedDay.xpDeltas.Fitness > 0)
    previousHash = record.hash
end

local repeatedJob = assert(Benchmark.begin(3))
repeatedJob.sliceStarted = 1000
while not repeatedJob.done do
    local ok, errorMessage = coroutine.resume(repeatedJob.thread)
    assert(ok, errorMessage)
end
assert(repeatedJob.ok == true)
assert(encodeCalls == 3)

local extendedJob = assert(Benchmark.begin(5))
extendedJob.sliceStarted = 1000
while not extendedJob.done do
    local ok, errorMessage = coroutine.resume(extendedJob.thread)
    assert(ok, errorMessage)
end
assert(extendedJob.ok == true)
assert(encodeCalls == 5)
assert(#capturedOptions.ledger.records == 5)

print("synthetic export benchmark test passed")
