local Identity = require "TGSRR/Run/Identity"
local Ledger = require "TGSRR/Run/Ledger"
local ExportCodec = require "TGSRR/Run/ExportCodec"

local Exporter = {}

local ROOT = "TGSRR/Runs"
local SLICE_MILLISECONDS = 8

local function milliseconds()
    if getTimestampMs then return getTimestampMs() end
    return os.clock() * 1000
end

function Exporter.generate(run, work)
    run = run or Identity.get()
    if not run or not run.runId then return false, "missing_active_run" end
    local codecOk, codecError = ExportCodec.selfTest(work)
    if not codecOk then return false, codecError end

    local ledger, ledgerError = Ledger.readAll(run, work)
    if not ledger then return false, ledgerError end
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil
    local projection = {
        currentKills = math.max(0, tonumber(player and player:getZombieKills()) or 0),
    }
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
            or decoded.currentKills ~= projection.currentKills then
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
