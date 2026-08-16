local capturedOptions = nil

package.loaded["TGSRR/Run/Identity"] = {
    get = function()
        return {
            runId = "rr-benchmark-test",
            epoch = 1,
            eventSequence = 0,
            eventHash = string.rep("0", 64),
        }
    end,
    utcSeconds = function() return 1000 end,
}
package.loaded["TGSRR/Run/Ledger"] = {
    readAll = function()
        return {
            runId = "rr-benchmark-test",
            eventSequence = 0,
            eventHash = string.rep("0", 64),
            records = {},
        }
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

local Benchmark = require "TGSRR/Run/SyntheticExportBenchmark"
local EventCodec = require "TGSRR/Run/EventCodec"
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

print("synthetic export benchmark test passed")
