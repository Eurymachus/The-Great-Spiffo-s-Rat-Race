local EventCodec = require "TGSRR/Run/EventCodec"
local RecoveryStore = require "TGSRR/Run/RecoveryStore"

local Ledger = {}

local ROOT = "TGSRR/Runs"
local SEGMENT_FORMAT = 1
local EVENTS_PER_SEGMENT = 256

local function segmentPath(runId, index, epoch)
    if tonumber(epoch) and tonumber(epoch) > 1 then
        return RecoveryStore.segmentPath(runId, epoch, index)
    end
    return ROOT .. "/" .. tostring(runId) .. "/segments/events-"
        .. string.format("%06d", index) .. ".log"
end

local function textExists(filename)
    local reader = getFileReader(filename, false)
    if not reader then return false end
    reader:close()
    return true
end

local function hexEncode(value)
    return (tostring(value or ""):gsub(".", function(character)
        return string.format("%02x", string.byte(character))
    end))
end

local function hexDecode(value)
    value = tostring(value or "")
    if #value % 2 ~= 0 or value:find("[^0-9a-f]") then return nil, "invalid_record_encoding" end
    return (value:gsub("..", function(pair) return string.char(tonumber(pair, 16)) end))
end

local function recordLine(sequence, record)
    return table.concat({
        "R", tostring(sequence), record.previousHash, record.hash,
        tostring(#record.body), hexEncode(record.body),
    }, "|") .. "\n"
end

local function sealLine(count, sequence, hash)
    return table.concat({ "S", tostring(count), tostring(sequence), hash }, "|") .. "\n"
end

local function readSegment(runId, index, expectedPreviousHash,
        verifyHashes, collectRecords, work, epoch)
    local reader = getFileReader(segmentPath(runId, index, epoch), false)
    if not reader then return nil, "missing_event_segment:" .. tostring(index) end

    local line = reader:readLine()
    local format, storedIndex, startSequence, startHash = nil, nil, nil, nil
    if line then
        format, storedIndex, startSequence, startHash =
            line:match("^H|(%d+)|(%d+)|(%d+)|([0-9a-f]+)$")
    end
    if tonumber(format) ~= SEGMENT_FORMAT or tonumber(storedIndex) ~= index then
        reader:close()
        return nil, "invalid_segment_header:" .. tostring(index)
    end
    if expectedPreviousHash and startHash ~= expectedPreviousHash then
        reader:close()
        return nil, "segment_chain_discontinuity:" .. tostring(index)
    end

    local count = 0
    local previousHash = startHash
    local finalSequence = tonumber(startSequence) - 1
    local sealed = false
    local records = collectRecords and {} or nil
    line = reader:readLine()
    while line do
        if sealed then reader:close(); return nil, "frame_after_segment_seal" end
        if line:sub(1, 2) == "R|" then
            local sequenceText, recordPrevious, hash, lengthText, encoded =
                line:match("^R|(%d+)|([0-9a-f]+)|([0-9a-f]+)|(%d+)|([0-9a-f]*)$")
            if not sequenceText then reader:close(); return nil, "truncated_or_invalid_record" end
            local sequence = tonumber(sequenceText)
            if sequence ~= tonumber(startSequence) + count then
                reader:close(); return nil, "event_sequence_mismatch:" .. tostring(sequenceText)
            end
            if recordPrevious ~= previousHash then
                reader:close(); return nil, "chain_discontinuity:" .. tostring(sequence)
            end
            local body, decodeError = hexDecode(encoded)
            if not body then reader:close(); return nil, decodeError end
            if #body ~= tonumber(lengthText) then reader:close(); return nil, "record_length_mismatch" end
            local record = { previousHash = recordPrevious, hash = hash, body = body }
            if verifyHashes ~= false then
                local verified, verifyError = EventCodec.verify(record, previousHash, work)
                if not verified then reader:close(); return nil, verifyError .. ":" .. tostring(sequence) end
            end
            if records then records[#records + 1] = record end
            count = count + 1
            finalSequence = sequence
            previousHash = hash
        elseif line:sub(1, 2) == "S|" then
            local countText, sequenceText, hash = line:match("^S|(%d+)|(%d+)|([0-9a-f]+)$")
            if not countText or tonumber(countText) ~= count or tonumber(sequenceText) ~= finalSequence
                    or hash ~= previousHash then
                reader:close(); return nil, "invalid_segment_seal:" .. tostring(index)
            end
            sealed = true
        else
            reader:close()
            return nil, "invalid_segment_frame:" .. tostring(index)
        end
        line = reader:readLine()
    end
    reader:close()

    if count == 0 then return nil, "empty_event_segment:" .. tostring(index) end
    if count > EVENTS_PER_SEGMENT then return nil, "oversized_event_segment:" .. tostring(index) end
    if count == EVENTS_PER_SEGMENT and not sealed then return nil, "missing_segment_seal:" .. tostring(index) end
    if count < EVENTS_PER_SEGMENT and sealed then return nil, "premature_segment_seal:" .. tostring(index) end
    return {
        index = index,
        count = count,
        startSequence = tonumber(startSequence),
        startHash = startHash,
        finalSequence = finalSequence,
        finalHash = previousHash,
        sealed = sealed,
        records = records,
    }
end

local function appendRecord(runId, sequence, record, epoch, checkpointSequence)
    epoch = math.max(1, math.floor(tonumber(epoch) or 1))
    checkpointSequence = epoch > 1
        and math.max(0, math.floor(tonumber(checkpointSequence) or 0)) or 0
    local branchSequence = sequence - checkpointSequence
    if branchSequence < 1 then return false, "invalid_branch_event_sequence" end
    local segmentIndex =
        math.floor((branchSequence - 1) / EVENTS_PER_SEGMENT) + 1
    local position = ((branchSequence - 1) % EVENTS_PER_SEGMENT) + 1
    local filename = segmentPath(runId, segmentIndex, epoch)
    local writer = nil

    if position == 1 then
        if textExists(filename) then return false, "event_segment_already_exists" end
        writer = getFileWriter(filename, true, false)
        if not writer then return false, "unable_to_create_event_segment" end
        writer:write(table.concat({
            "H", tostring(SEGMENT_FORMAT), tostring(segmentIndex), tostring(sequence), record.previousHash,
        }, "|") .. "\n")
    else
        local segment, readError = readSegment(
            runId, segmentIndex, nil, false, nil, nil, epoch)
        if not segment then return false, readError end
        if segment.sealed or segment.count ~= position - 1 or segment.finalHash ~= record.previousHash then
            return false, "active_segment_cursor_mismatch"
        end
        writer = getFileWriter(filename, false, true)
        if not writer then return false, "unable_to_append_event_segment" end
    end

    writer:write(recordLine(sequence, record))
    if position == EVENTS_PER_SEGMENT then writer:write(sealLine(position, sequence, record.hash)) end
    writer:close()

    local written, verifyError = readSegment(
        runId, segmentIndex, nil, false, nil, nil, epoch)
    if not written then return false, verifyError end
    if written.count ~= position or written.finalSequence ~= sequence or written.finalHash ~= record.hash then
        return false, "event_segment_readback_mismatch"
    end
    return true
end

local function readRootPrefix(runId, sequence, work)
    if sequence == 0 then
        return {
            records = {},
            eventHash = EventCodec.GENESIS_HASH,
        }
    end
    local records = {}
    local previousHash = EventCodec.GENESIS_HASH
    local index = 1
    while #records < sequence do
        local segment, readError = readSegment(
            runId, index, previousHash, true, true, work, 1)
        if not segment then return nil, readError end
        for _, record in ipairs(segment.records) do
            records[#records + 1] = record
        end
        previousHash = segment.finalHash
        index = index + 1
    end
    local prefix = {}
    for recordIndex = 1, sequence do
        prefix[recordIndex] = records[recordIndex]
    end
    return {
        records = prefix,
        eventHash = prefix[sequence].hash,
    }
end

local function readBranch(run, collectRecords, work)
    local epoch = math.max(1, math.floor(tonumber(run.epoch) or 1))
    local checkpointSequence = math.max(0,
        math.floor(tonumber(run.branchCheckpointSequence) or 0))
    local checkpointHash = tostring(
        run.branchCheckpointHash or EventCodec.GENESIS_HASH):lower()
    local sequence = math.max(0, math.floor(tonumber(run.eventSequence) or 0))
    local expectedCount = sequence - checkpointSequence
    if expectedCount < 0 then return nil, "invalid_branch_cursor" end

    local previousHash = checkpointHash
    local consumed = 0
    local records = collectRecords and {} or nil
    local segmentCount = math.ceil(expectedCount / EVENTS_PER_SEGMENT)
    for index = 1, segmentCount do
        local segment, readError = readSegment(
            run.runId, index, previousHash, true,
            collectRecords, work, epoch)
        if not segment then return nil, readError end
        local expectedStart = checkpointSequence
            + (index - 1) * EVENTS_PER_SEGMENT + 1
        if segment.startSequence ~= expectedStart then
            return nil, "branch_segment_sequence_mismatch:" .. tostring(index)
        end
        consumed = consumed + segment.count
        previousHash = segment.finalHash
        if records then
            for _, record in ipairs(segment.records) do
                records[#records + 1] = record
            end
        end
    end
    if consumed ~= expectedCount then
        return nil, "event_segment_ahead_of_save"
    end
    if textExists(segmentPath(run.runId, segmentCount + 1, epoch)) then
        return nil, "event_segment_ahead_of_save"
    end
    return {
        records = records,
        eventHash = previousHash,
        eventSequence = sequence,
    }
end

local function readStoredEpoch(run, work)
    local epoch = math.max(1, math.floor(tonumber(run.epoch) or 1))
    local checkpointSequence = epoch > 1 and math.max(0,
        math.floor(tonumber(run.branchCheckpointSequence) or 0)) or 0
    local previousHash = epoch > 1
        and tostring(run.branchCheckpointHash or ""):lower()
        or EventCodec.GENESIS_HASH
    local records = {}
    local index = 1
    while textExists(segmentPath(run.runId, index, epoch)) do
        local segment, readError = readSegment(
            run.runId, index, previousHash, true, true, work, epoch)
        if not segment then return nil, readError end
        local expectedStart = checkpointSequence
            + (index - 1) * EVENTS_PER_SEGMENT + 1
        if segment.startSequence ~= expectedStart then
            return nil, "branch_segment_sequence_mismatch:" .. tostring(index)
        end
        for _, record in ipairs(segment.records) do
            records[#records + 1] = record
        end
        previousHash = segment.finalHash
        index = index + 1
    end
    return {
        epoch = epoch,
        checkpointSequence = checkpointSequence,
        checkpointHash = epoch > 1
            and tostring(run.branchCheckpointHash):lower()
            or EventCodec.GENESIS_HASH,
        records = records,
        eventSequence = checkpointSequence + #records,
        eventHash = previousHash,
    }
end

local function readEpochPrefix(runId, epoch, sequence, work)
    if epoch == 1 then return readRootPrefix(runId, sequence, work) end
    local metadata, metadataError =
        RecoveryStore.read(runId, epoch, work)
    if not metadata then return nil, metadataError end
    if sequence < metadata.checkpointSequence then
        return readEpochPrefix(
            runId, metadata.parentEpoch, sequence, work)
    end
    local parent, parentError = readEpochPrefix(
        runId,
        metadata.parentEpoch,
        metadata.checkpointSequence,
        work
    )
    if not parent then return nil, parentError end
    if parent.eventHash ~= metadata.checkpointHash then
        return nil, "recovery_checkpoint_hash_mismatch"
    end
    local stored, storedError = readStoredEpoch({
        runId = runId,
        epoch = epoch,
        branchCheckpointSequence = metadata.checkpointSequence,
        branchCheckpointHash = metadata.checkpointHash,
    }, work)
    if not stored then return nil, storedError end
    local required = sequence - metadata.checkpointSequence
    if required > #stored.records then
        return nil, "event_segment_behind_save"
    end
    local records = parent.records
    for position = 1, required do
        records[#records + 1] = stored.records[position]
    end
    return {
        records = records,
        eventHash = required == 0
            and metadata.checkpointHash
            or stored.records[required].hash,
    }
end

function Ledger.initialize(run, work)
    local sequence = tonumber(run.eventSequence) or 0
    local expectedHash = tostring(run.eventHash or EventCodec.GENESIS_HASH):lower()
    local epoch = math.max(1, math.floor(tonumber(run.epoch) or 1))
    if sequence < 0 or sequence % 1 ~= 0 then return false, "invalid_event_cursor" end
    if #expectedHash ~= 64 or not expectedHash:match("^[0-9a-f]+$") then
        return false, "invalid_event_hash_cursor"
    end

    if epoch > 1 then
        local metadata, metadataError =
            RecoveryStore.read(run.runId, epoch, work)
        if not metadata then return false, metadataError end
        local checkpointSequence = math.max(0,
            math.floor(tonumber(run.branchCheckpointSequence) or -1))
        local checkpointHash = tostring(run.branchCheckpointHash or ""):lower()
        if checkpointSequence ~= metadata.checkpointSequence
                or checkpointHash ~= metadata.checkpointHash then
            return false, "recovery_checkpoint_cursor_mismatch"
        end
        local prefix, prefixError = readEpochPrefix(
            run.runId,
            metadata.parentEpoch,
            checkpointSequence,
            work
        )
        if not prefix then return false, prefixError end
        if prefix.eventHash ~= checkpointHash then
            return false, "recovery_checkpoint_hash_mismatch"
        end
        local branch, branchError = readBranch(run, false, work)
        if not branch then return false, branchError end
        if branch.eventHash ~= expectedHash then
            return false, "event_hash_cursor_mismatch"
        end
        return true
    end

    local previousHash = EventCodec.GENESIS_HASH
    local consumed = 0
    local segmentCount = math.ceil(sequence / EVENTS_PER_SEGMENT)
    for index = 1, segmentCount do
        local segment, readError = readSegment(run.runId, index, previousHash, nil, nil, work)
        if not segment then return false, readError end
        consumed = consumed + segment.count
        previousHash = segment.finalHash
    end
    if consumed ~= sequence then return false, "event_segment_ahead_of_save" end
    if previousHash ~= expectedHash then return false, "event_hash_cursor_mismatch" end
    if textExists(segmentPath(run.runId, segmentCount + 1, 1)) then return false, "event_segment_ahead_of_save" end
    return true
end

function Ledger.inspectAhead(run, work)
    local stored, storedError = readStoredEpoch(run, work)
    if not stored then return nil, storedError end
    local savedSequence = math.max(0,
        math.floor(tonumber(run.eventSequence) or 0))
    local savedHash = tostring(
        run.eventHash or EventCodec.GENESIS_HASH):lower()
    if savedSequence < stored.checkpointSequence then
        return nil, "save_predates_active_branch_checkpoint"
    end
    local savedPosition = savedSequence - stored.checkpointSequence
    if savedPosition > #stored.records then
        return nil, "event_segment_behind_save"
    end
    local observedSavedHash = savedPosition == 0
        and stored.checkpointHash
        or stored.records[savedPosition].hash
    if observedSavedHash ~= savedHash then
        return nil, "event_hash_cursor_mismatch"
    end
    if stored.eventSequence <= savedSequence then
        return nil, "no_event_tail_ahead_of_save"
    end

    local tail = {}
    local eventTypes = {}
    local eventTypeCounts = {}
    for position = savedPosition + 1, #stored.records do
        local record = stored.records[position]
        local inspected, inspectError = EventCodec.inspectBody(record.body)
        if not inspected then return nil, inspectError end
        tail[#tail + 1] = record
        if not eventTypeCounts[inspected.eventType] then
            eventTypes[#eventTypes + 1] = inspected.eventType
            eventTypeCounts[inspected.eventType] = 0
        end
        eventTypeCounts[inspected.eventType] =
            eventTypeCounts[inspected.eventType] + 1
    end
    table.sort(eventTypes)
    return {
        epoch = stored.epoch,
        checkpointSequence = savedSequence,
        checkpointHash = savedHash,
        supersededEventSequence = stored.eventSequence,
        supersededEventHash = stored.eventHash,
        tail = tail,
        eventTypes = eventTypes,
        eventTypeCounts = eventTypeCounts,
    }
end

function Ledger.beginRecovery(run, decision, work)
    decision = decision or {}
    local ahead, aheadError = Ledger.inspectAhead(run, work)
    if not ahead then return false, aheadError end
    local existing, continuationError = RecoveryStore.findContinuation(
        run.runId, ahead.epoch, ahead.checkpointSequence,
        ahead.checkpointHash, ahead.supersededEventSequence,
        ahead.supersededEventHash, work)
    if existing == nil then return false, continuationError end
    local epoch, epochError
    if existing then
        epoch = existing.epoch
    else
        epoch, epochError = RecoveryStore.nextEpoch(run.runId, work)
        if not epoch then return false, epochError end
    end
    local metadata = {
        epoch = epoch,
        parentEpoch = ahead.epoch,
        checkpointSequence = ahead.checkpointSequence,
        checkpointHash = ahead.checkpointHash,
        supersededEventSequence = ahead.supersededEventSequence,
        supersededEventHash = ahead.supersededEventHash,
        createdUtc = math.max(0,
            math.floor(tonumber(decision.utc) or 0)),
        reason = tostring(decision.reason or "save_rollback"),
        decider = {
            type = tostring(decision.deciderType or "player"),
            id = tostring(decision.deciderId or "local_player"),
        },
        authorizationStatus = tostring(
            decision.authorizationStatus or "unapproved"),
        selectedAction = tostring(decision.selectedAction or "resume"),
        supersededEventTypes = ahead.eventTypes,
        supersededEventTypeCounts = ahead.eventTypeCounts,
    }
    local writeResult = existing
    if not existing then
        local written
        written, writeResult =
            RecoveryStore.write(run.runId, metadata, work)
        if not written then return false, writeResult end
    end

    run.epoch = epoch
    run.parentEpoch = ahead.epoch
    run.branchCheckpointSequence = ahead.checkpointSequence
    run.branchCheckpointHash = ahead.checkpointHash
    run.eventSequence = ahead.checkpointSequence
    run.eventHash = ahead.checkpointHash
    run.integrityStatus = "recovery_pending"
    return true, writeResult, existing and true or false
end

function Ledger.hasRecoveryDecision(run, epoch, work)
    local stored, storedError = readStoredEpoch(run, work)
    if not stored then return nil, storedError end
    epoch = tonumber(epoch) or tonumber(run.epoch) or 1
    for _, record in ipairs(stored.records) do
        local inspected, inspectError = EventCodec.inspectBody(record.body)
        if not inspected then return nil, inspectError end
        if inspected.eventType == "run.recovery.decided"
                and inspected.epoch == epoch then
            return true
        end
    end
    return false
end

local function epochRun(runId, epoch, work)
    if epoch == 1 then
        return {
            runId = runId,
            epoch = 1,
            branchCheckpointSequence = 0,
            branchCheckpointHash = EventCodec.GENESIS_HASH,
        }
    end
    local metadata, metadataError =
        RecoveryStore.read(runId, epoch, work)
    if not metadata then return nil, metadataError end
    return {
        runId = runId,
        epoch = epoch,
        branchCheckpointSequence = metadata.checkpointSequence,
        branchCheckpointHash = metadata.checkpointHash,
    }
end

function Ledger.recoveryEvidence(run, work, activeRecords)
    local metadataList, metadataError =
        RecoveryStore.readAll(run.runId, work)
    if not metadataList then return nil, metadataError end
    local recoveries = {}
    for _, metadata in ipairs(metadataList) do
        local parentRun, parentError =
            epochRun(run.runId, metadata.parentEpoch, work)
        if not parentRun then return nil, parentError end
        local stored, storedError = readStoredEpoch(parentRun, work)
        if not stored then return nil, storedError end
        if stored.eventSequence ~= metadata.supersededEventSequence
                or stored.eventHash ~= metadata.supersededEventHash then
            return nil, "superseded_branch_head_mismatch:"
                .. tostring(metadata.epoch)
        end
        local startPosition = metadata.checkpointSequence
            - stored.checkpointSequence + 1
        if startPosition < 1 then
            return nil, "superseded_branch_checkpoint_mismatch"
        end
        local bodies = {}
        for position = startPosition, #stored.records do
            bodies[#bodies + 1] = stored.records[position].body
        end
        recoveries[#recoveries + 1] = {
            epoch = metadata.epoch,
            parentEpoch = metadata.parentEpoch,
            checkpointSequence = metadata.checkpointSequence,
            checkpointHash = metadata.checkpointHash,
            supersededEventSequence =
                metadata.supersededEventSequence,
            supersededEventHash = metadata.supersededEventHash,
            supersededBodies = bodies,
            createdUtc = metadata.createdUtc,
            reason = metadata.reason,
            decider = metadata.decider,
            authorizationStatus = metadata.authorizationStatus,
            selectedAction = metadata.selectedAction,
            supersededEventTypes = metadata.supersededEventTypes,
            supersededEventTypeCounts =
                metadata.supersededEventTypeCounts,
            metadataChecksum = metadata.checksum,
        }
    end
    local decisions = {}
    for sequence, record in ipairs(activeRecords or {}) do
        local inspected, inspectError = EventCodec.inspectBody(record.body)
        if not inspected then return nil, inspectError end
        if inspected.eventType == "run.recovery.decided" then
            local payload, payloadError =
                EventCodec.decodePayload(inspected.canonicalPayload)
            if not payload then return nil, payloadError end
            decisions[#decisions + 1] = {
                sequence = sequence,
                epoch = inspected.epoch,
                utc = inspected.utc,
                worldAgeHours = inspected.worldAgeHours,
                reason = payload.reason,
                decider = payload.decider,
                authorizationStatus = payload.authorizationStatus,
                selectedAction = payload.selectedAction,
            }
        end
    end
    local present = #recoveries > 0 or #decisions > 0
    return {
        schema = 1,
        present = present,
        hasBranches = #recoveries > 0,
        status = present and "recovery_present" or "uninterrupted",
        activeEpoch = math.max(1,
            math.floor(tonumber(run.epoch) or 1)),
        recoveries = recoveries,
        decisions = decisions,
    }
end

function Ledger.reconcileInterruptedSessions(run, fileSessionSequence, work)
    local savedSequence = math.max(0,
        math.floor(tonumber(run.eventSequence) or 0))
    local savedHash = tostring(
        run.eventHash or EventCodec.GENESIS_HASH):lower()
    local savedSessionSequence = math.max(0,
        math.floor(tonumber(run.sessionSequence) or 0))
    fileSessionSequence = tonumber(fileSessionSequence)
    if not fileSessionSequence or fileSessionSequence < savedSessionSequence
            or fileSessionSequence % 1 ~= 0 then
        return false, "interrupted_session_history_mismatch"
    end

    local ahead, aheadError = Ledger.inspectAhead(run, work)
    if not ahead then return false, aheadError end

    local observedSessionSequence = savedSessionSequence
    local recoveredSessions = 0
    for offset, record in ipairs(ahead.tail) do
        local recordIndex = savedSequence + offset
        local inspected, inspectError =
            EventCodec.inspectBody(record.body)
        if not inspected then return false, inspectError end
        if inspected.runId ~= tostring(run.runId)
                or inspected.sequence ~= recordIndex then
            return false, "interrupted_session_event_identity_mismatch"
        end
        if inspected.eventType == "session.started" then
            local payload, payloadError =
                EventCodec.decodePayload(inspected.canonicalPayload)
            if not payload then return false, payloadError end
            local sessionSequence = tonumber(payload.sessionSequence)
            if not sessionSequence
                    or sessionSequence ~= observedSessionSequence + 1 then
                return false, "interrupted_session_sequence_mismatch"
            end
            observedSessionSequence = sessionSequence
            recoveredSessions = recoveredSessions + 1
        elseif inspected.eventType ~= "run.recovery.decided" then
            -- Gameplay-bearing tails are genuine rollback branches and must
            -- never be silently adopted as an interrupted session commit.
            return false, "rollback_requires_declared_recovery"
        end
    end
    if observedSessionSequence ~= fileSessionSequence then
        return false, "interrupted_session_file_cursor_mismatch"
    end

    run.eventSequence = ahead.supersededEventSequence
    run.eventHash = ahead.supersededEventHash
    run.sessionSequence = observedSessionSequence
    run.integrityStatus = "ok"
    return true, {
        savedEventSequence = savedSequence,
        savedEventHash = savedHash,
        adoptedEventSequence = ahead.supersededEventSequence,
        adoptedEventHash = ahead.supersededEventHash,
        savedSessionSequence = savedSessionSequence,
        adoptedSessionSequence = observedSessionSequence,
        recoveredSessions = recoveredSessions,
    }
end

function Ledger.append(run, event)
    local sequence = (tonumber(run.eventSequence) or 0) + 1
    event.sequence = sequence
    event.runId = run.runId
    event.epoch = tonumber(run.epoch) or 1

    local previousHash = tostring(run.eventHash or EventCodec.GENESIS_HASH):lower()
    local record, encodeError = EventCodec.encode(event, previousHash)
    if not record then return false, encodeError end
    local written, writeError = appendRecord(
        run.runId,
        sequence,
        record,
        tonumber(run.epoch) or 1,
        tonumber(run.branchCheckpointSequence) or 0
    )
    if not written then return false, writeError end
    return true, { sequence = sequence, hash = record.hash }
end

function Ledger.readAll(run, work)
    local initialized, initializeError = Ledger.initialize(run, work)
    if not initialized then return nil, initializeError end

    local sequence = tonumber(run.eventSequence) or 0
    local epoch = math.max(1, math.floor(tonumber(run.epoch) or 1))
    if epoch > 1 then
        local active, activeError =
            readEpochPrefix(run.runId, epoch, sequence, work)
        if not active then return nil, activeError end
        if #active.records ~= sequence then
            return nil, "export_event_count_mismatch"
        end
        return {
            runId = tostring(run.runId),
            eventSequence = sequence,
            eventHash = active.eventHash,
            records = active.records,
        }
    end

    local previousHash = EventCodec.GENESIS_HASH
    local records = {}
    local segmentCount = math.ceil(sequence / EVENTS_PER_SEGMENT)
    for index = 1, segmentCount do
        local segment, readError = readSegment(run.runId, index, previousHash, true, true, work)
        if not segment then return nil, readError end
        for _, record in ipairs(segment.records) do records[#records + 1] = record end
        previousHash = segment.finalHash
    end
    if #records ~= sequence then return nil, "export_event_count_mismatch" end
    return {
        runId = tostring(run.runId),
        eventSequence = sequence,
        eventHash = previousHash,
        records = records,
    }
end

Ledger.eventsPerSegment = EVENTS_PER_SEGMENT
Ledger.segmentFormat = SEGMENT_FORMAT

return Ledger
