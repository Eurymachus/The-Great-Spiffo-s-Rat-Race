local files = {}

local function readerFor(value)
    local lines = {}
    for line in tostring(value or ""):gmatch("([^\n]*)\n") do
        lines[#lines + 1] = line
    end
    local index = 0
    return {
        readLine = function()
            index = index + 1
            return lines[index]
        end,
        close = function() end,
    }
end

function getFileReader(filename)
    if files[filename] == nil then return nil end
    return readerFor(files[filename])
end

function getFileWriter(filename, _, append)
    local chunks = {}
    if append and files[filename] then chunks[1] = files[filename] end
    return {
        write = function(_, value)
            chunks[#chunks + 1] = value
        end,
        close = function()
            files[filename] = table.concat(chunks)
        end,
    }
end

function getFileInput()
    return nil
end

local EventCodec = require "TGSRR/Run/EventCodec"
local Ledger = require "TGSRR/Run/Ledger"

local run = {
    runId = "rr-recovery-test",
    epoch = 1,
    eventSequence = 0,
    eventHash = EventCodec.GENESIS_HASH,
    sessionSequence = 0,
}

local function append(eventType, payload)
    local ok, result = Ledger.append(run, {
        utc = 1000 + run.eventSequence,
        worldAgeHours = run.eventSequence,
        eventType = eventType,
        payload = payload or {},
    })
    assert(ok, result)
    run.eventSequence = result.sequence
    run.eventHash = result.hash
end

append("session.started", { sessionSequence = 1 })
run.sessionSequence = 1
local checkpointOneHash = run.eventHash
append("day.started", { dayIndex = 2 })

run.eventSequence = 1
run.eventHash = checkpointOneHash
local aheadOne = assert(Ledger.inspectAhead(run))
assert(aheadOne.supersededEventSequence == 2)
assert(aheadOne.eventTypes[1] == "day.started")

local recoveredOne, metadataOne = Ledger.beginRecovery(run, {
    utc = 2000,
    reason = "save_rollback",
    deciderType = "player",
    deciderId = "local_player",
    authorizationStatus = "unapproved",
    selectedAction = "resume",
})
assert(recoveredOne, metadataOne)
assert(run.epoch == 2 and run.eventSequence == 1)

-- A crash after immutable branch creation but before the save records epoch 2
-- must resume that branch instead of manufacturing another recovery.
run.epoch = 1
run.parentEpoch = nil
run.branchCheckpointSequence = nil
run.branchCheckpointHash = nil
run.eventSequence = 1
run.eventHash = checkpointOneHash
local resumedOne, resumedMetadata, reusedOne = Ledger.beginRecovery(run, {
    utc = 2001,
    reason = "save_rollback",
    deciderType = "player",
    deciderId = "local_player",
    authorizationStatus = "unapproved",
    selectedAction = "resume",
})
assert(resumedOne, resumedMetadata)
assert(reusedOne == true)
assert(resumedMetadata.epoch == metadataOne.epoch)
assert(run.epoch == 2 and run.eventSequence == 1)

append("run.recovery.decided", {
    reason = metadataOne.reason,
    epoch = metadataOne.epoch,
})
local epochTwoCheckpointHash = run.eventHash
append("town.visited", { townId = "rosewood" })

run.eventSequence = 2
run.eventHash = epochTwoCheckpointHash
local aheadTwo = assert(Ledger.inspectAhead(run))
assert(aheadTwo.epoch == 2)
assert(aheadTwo.supersededEventSequence == 3)
assert(aheadTwo.eventTypes[1] == "town.visited")

local recoveredTwo, metadataTwo = Ledger.beginRecovery(run, {
    utc = 3000,
    reason = "save_rollback",
    deciderType = "moderator",
    deciderId = "test-moderator",
    authorizationStatus = "approved",
    selectedAction = "resume",
})
assert(recoveredTwo, metadataTwo)
assert(run.epoch == 3 and run.eventSequence == 2)
append("run.recovery.decided", {
    reason = metadataTwo.reason,
    epoch = metadataTwo.epoch,
})

local initialized, initializeError = Ledger.initialize(run)
assert(initialized, initializeError)
local active = assert(Ledger.readAll(run))
assert(#active.records == 3)
for sequence, record in ipairs(active.records) do
    local event = assert(EventCodec.inspectBody(record.body))
    assert(event.sequence == sequence)
end

local evidence = assert(Ledger.recoveryEvidence(run, nil, active.records))
assert(evidence.present == true)
assert(evidence.hasBranches == true)
assert(evidence.activeEpoch == 3)
assert(#evidence.recoveries == 2)
assert(#evidence.decisions == 2)
assert(#evidence.recoveries[1].supersededBodies == 1)
assert(#evidence.recoveries[2].supersededBodies == 1)
assert(evidence.recoveries[1].decider.type == "player")
assert(evidence.recoveries[2].decider.type == "moderator")

print("recovery branch test passed")
