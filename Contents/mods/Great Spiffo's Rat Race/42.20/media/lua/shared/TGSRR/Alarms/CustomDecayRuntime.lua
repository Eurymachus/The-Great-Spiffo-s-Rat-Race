local Runtime = {}
local ChallengeContext = require "TGSRR/Challenge/Context"

local MOD_DATA_KEY = "TGSRR_CustomAlarmDecay"
local SCHEMA_VERSION = 1
local debugOriginalElecModifier = nil
local pendingRoomNullifiers = {}
local pendingChunkClaims = {}
local pendingChunkRescans = {}
local recordRevision = 0
local CHUNK_RESCAN_LIMIT = 6

local function recordsChanged()
    recordRevision = recordRevision + 1
end

local function integer(value, fallback)
    return math.floor(tonumber(value) or fallback or 0)
end

local function configuration()
    local options = SandboxVars and SandboxVars.TGSRRAlarmDecay or nil
    local minimum = math.max(0, integer(options and options.MinimumDay, 0))
    local maximum = math.max(0, integer(options and options.MaximumDay, 730))
    if maximum < minimum then minimum, maximum = maximum, minimum end

    return {
        enabled = options ~= nil and options.Enabled == true,
        minimum = minimum,
        maximum = maximum,
    }
end

local function randomInclusive(minimum, maximum)
    if maximum <= minimum then return minimum end
    return ZombRand(minimum, maximum + 1)
end

local function expiryDay(powerShutoffDay, minimum, maximum)
    return integer(powerShutoffDay, 0) + randomInclusive(minimum, maximum)
end

local function isLive(record, worldAgeDays)
    return record ~= nil
        and record.pending ~= true
        and record.triggered ~= true
        and tonumber(record.expiryDay) ~= nil
        and tonumber(worldAgeDays) <= tonumber(record.expiryDay)
end

local function authoritative()
    return not (isClient and isClient())
end

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
        data.minimum = nil
        data.maximum = nil
        data.buildings = {}
    end
    data.buildings = data.buildings or {}
    return data
end

local function buildingKey(building)
    if not building then return nil end
    if building.getIDString then return tostring(building:getIDString()) end
    if building.getID then return tostring(building:getID()) end
    return tostring(building:getX()) .. ":" .. tostring(building:getY())
end

local function forEachBuilding(callback)
    local world = getWorld and getWorld() or nil
    local metaGrid = world and world:getMetaGrid() or nil
    local buildings = metaGrid and metaGrid:getBuildings() or nil
    if not buildings then return 0 end

    local count = 0
    for i = 0, buildings:size() - 1 do
        local building = buildings:get(i)
        if building then
            callback(building)
            count = count + 1
        end
    end
    return count
end

local function worldAgeDays()
    local gameTime = getGameTime and getGameTime() or nil
    return gameTime and gameTime:getWorldAgeHours() / 24 or 0
end

local function powerShutoffDay()
    return integer(SandboxVars and SandboxVars.ElecShutModifier, 14)
end

local function setElectricityShutoffDay(value)
    local options = getSandboxOptions and getSandboxOptions() or nil
    local option = options and options:getOptionByName("ElecShutModifier")
        or nil
    if option then option:setValue(value) end
    if SandboxVars then SandboxVars.ElecShutModifier = value end
end

local function recordFor(building)
    local key = buildingKey(building)
    return key and root().buildings[key] or nil
end

local function buildingByKey(wantedKey, record)
    wantedKey = tostring(wantedKey)
    local found
    forEachBuilding(function(building)
        if not found and buildingKey(building) == wantedKey then
            found = building
        end
    end)

    -- Some runtime-adjusted BuildingDefs remain in the per-cell meta index
    -- used by chunk loading but are absent from the global consolidated list.
    -- Query the saved bounds through the same intersection API so diagnostics
    -- can still inspect those unloaded definitions. This is read-only.
    if not found and record and ArrayList then
        local world = getWorld and getWorld() or nil
        local metaGrid = world and world:getMetaGrid() or nil
        local x1 = tonumber(record.x1) or tonumber(record.x)
        local y1 = tonumber(record.y1) or tonumber(record.y)
        local x2 = tonumber(record.x2) or (x1 and x1 + 1)
        local y2 = tonumber(record.y2) or (y1 and y1 + 1)
        if metaGrid and x1 and y1 and x2 and y2 then
            local buildings = ArrayList.new()
            metaGrid:getBuildingsIntersecting(
                x1, y1, math.max(1, x2 - x1), math.max(1, y2 - y1),
                buildings)
            for i = 0, buildings:size() - 1 do
                local building = buildings:get(i)
                if buildingKey(building) == wantedKey then
                    found = building
                    break
                end
            end
        end
    end
    return found
end

local function chunkStreamingDetails(building)
    local cell = getCell and getCell() or nil
    if not building then return nil, nil, nil, "BuildingDef not resolved" end
    if not cell then return nil, nil, nil, "cell unavailable" end
    if not building.getRooms then
        return nil, nil, nil, "BuildingDef rooms unavailable"
    end

    local seen = {}
    local coordinates = {}
    local function addRooms(rooms)
        if not rooms then return end
        for roomIndex = 0, rooms:size() - 1 do
            local room = rooms:get(roomIndex)
            local rects = room and room.getRects and room:getRects() or nil
            if rects then
                for rectIndex = 0, rects:size() - 1 do
                    local rect = rects:get(rectIndex)
                    local minWX = math.floor((rect:getX() - 1) / 8)
                    local minWY = math.floor((rect:getY() - 1) / 8)
                    local maxWX = math.floor(rect:getX2() / 8)
                    local maxWY = math.floor(rect:getY2() / 8)
                    for wy = minWY, maxWY do
                        for wx = minWX, maxWX do
                            local key = tostring(wx) .. ":" .. tostring(wy)
                            if seen[key] ~= true then
                                seen[key] = true
                                coordinates[#coordinates + 1] = { wx, wy }
                            end
                        end
                    end
                end
            end
        end
    end

    -- Match BuildingDef.CalculateBounds(), which includes both ordinary rooms
    -- and empty-outside definitions in overlappedChunks.
    addRooms(building:getRooms())
    if building.getEmptyOutside then addRooms(building:getEmptyOutside()) end

    local total = #coordinates
    local loaded = 0
    local missing = {}
    for _, coordinate in ipairs(coordinates) do
        local wx = coordinate[1]
        local wy = coordinate[2]
        if cell:getChunk(wx, wy) then
            loaded = loaded + 1
        elseif #missing < 3 then
            missing[#missing + 1] = tostring(wx) .. "," .. tostring(wy)
        end
    end
    if total == 0 then
        return loaded, total, table.concat(missing, " "),
            "no room rectangles"
    end
    return loaded, total, table.concat(missing, " "), nil
end

local function restoreVanillaAlarms()
    local data = root()
    forEachBuilding(function(building)
        local record = data.buildings[buildingKey(building)]
        if record and record.triggered ~= true then
            building:setAlarmed(true)
        end
    end)
end

local function updateConfiguration(data, config)
    local rangeChanged = data.minimum ~= config.minimum
        or data.maximum ~= config.maximum
    data.minimum = config.minimum
    data.maximum = config.maximum
    if rangeChanged then
        for _, record in pairs(data.buildings) do
            if record.triggered ~= true then
                record.expiryDay = expiryDay(
                    powerShutoffDay(), config.minimum, config.maximum)
            end
        end
    end
    return rangeChanged
end

local function setRecordPosition(record, building)
    local room = building:getFirstRoom()
    record.x = room and room:getX() or building:getX()
    record.y = room and room:getY() or building:getY()
    record.z = room and room:getZ() or 0
    record.x1 = building:getX()
    record.y1 = building:getY()
    record.x2 = building.getX2 and building:getX2() or record.x1 + 1
    record.y2 = building.getY2 and building:getY2() or record.y1 + 1
end

local function buildingLogDetails(building, record)
    local key = buildingKey(building) or "unknown"
    local x1 = record and record.x1
        or (building and building.getX and building:getX())
    local y1 = record and record.y1
        or (building and building.getY and building:getY())
    local x2 = record and record.x2
        or (building and building.getX2 and building:getX2())
    local y2 = record and record.y2
        or (building and building.getY2 and building:getY2())
    local x = record and record.x or x1
    local y = record and record.y or y1
    local z = record and record.z or 0
    local expiry = record and record.expiryDay or "none"
    return "id=" .. tostring(key)
        .. " anchor=" .. tostring(x) .. "," .. tostring(y)
        .. "," .. tostring(z)
        .. " bounds=" .. tostring(x1) .. "," .. tostring(y1)
        .. "-" .. tostring(x2) .. "," .. tostring(y2)
        .. " expiryDay=" .. tostring(expiry)
end

local function logBuildingResult(result, source, building, record, chunk,
        detail)
    local chunkText = chunk and (" chunk=" .. tostring(chunk)) or ""
    local detailText = detail and (" " .. tostring(detail)) or ""
    print("[TGSRR Alarms] " .. tostring(result)
        .. " source=" .. tostring(source) .. chunkText .. " "
        .. buildingLogDetails(building, record) .. detailText)
end

local function claimBuilding(building, config, data)
    if not building then return false end
    local key = buildingKey(building)
    if not key then return false end
    local record = data.buildings[key]
    if not record and building:isAlarmed() then
        record = {
            pending = true,
            triggered = false,
            expiryDay = expiryDay(
                powerShutoffDay(), config.minimum, config.maximum),
        }
        setRecordPosition(record, building)
        data.buildings[key] = record
    end

    if not record then return false, "not_alarmed" end
    if building.isFullyStreamedIn
            and not building:isFullyStreamedIn() then
        return false, "partially_streamed"
    end
    -- Only interpret vanilla's alarm flag after every overlapping chunk is
    -- present. During streaming, false may only be an intermediate state.
    if record.pending == true and not building:isAlarmed() then
        data.buildings[key] = nil
        return false, "nullified"
    end

    local finalized = false
    if record.pending == true then
        record.pending = false
        if record.expiryDay == nil then
            record.expiryDay = expiryDay(
                powerShutoffDay(), config.minimum, config.maximum)
        end
        record.triggered = false
        finalized = true
    end

    if record then
        if record.x == nil or record.y == nil then
            setRecordPosition(record, building)
        end
        -- Once all chunk-time vanilla nullifiers have run, TGSRR owns the
        -- surviving alarm and prevents Java from applying alarmDecay.
        building:setAlarmed(false)
    end
    return finalized, finalized and "claimed" or "owned"
end

-- Snapshot every successful vanilla meta-grid alarm roll without disabling it.
-- LoadChunk later validates each pending candidate after vanilla nullifiers.
function Runtime.capture()
    if not authoritative() then return false, "not_authoritative" end

    if not ChallengeContext.isActive() then
        restoreVanillaAlarms()
        return false, "inactive"
    end

    local config = configuration()
    local data = root()
    if not config.enabled then
        restoreVanillaAlarms()
        return false, "disabled"
    end

    local rangeChanged = updateConfiguration(data, config)
    local pending = 0
    forEachBuilding(function(building)
        local key = buildingKey(building)
        local record = data.buildings[key]
        if building:isAlarmed() and not record then
            record = {
                pending = true,
                triggered = false,
                expiryDay = expiryDay(
                    powerShutoffDay(), config.minimum, config.maximum),
            }
            setRecordPosition(record, building)
            data.buildings[key] = record
            pending = pending + 1
        end
        if record then
            if record.x == nil or record.y == nil then
                setRecordPosition(record, building)
            end
            if record.pending ~= true then building:setAlarmed(false) end
        end
    end)

    if pending > 0 or rangeChanged then
        print("[TGSRR Alarms] Snapshotted " .. tostring(pending)
            .. " successful vanilla alarm rolls; custom range "
            .. tostring(config.minimum) .. "-" .. tostring(config.maximum)
            .. " days after power shutoff.")
    end
    if pending > 0 or rangeChanged then recordsChanged() end
    return true, pending
end

function Runtime.onLoadChunk(chunk, deferredRescan)
    if not authoritative() or not ChallengeContext.isActive()
            or not chunk then return false end
    local config = configuration()
    local data = root()
    if not config.enabled then return false end
    updateConfiguration(data, config)

    local seen = {}
    local captured = 0
    local removed = 0
    local queued = 0
    local chunkWX
    local chunkWY
    if deferredRescan ~= true then
        pendingChunkRescans[chunk] = {
            chunk = chunk,
            delay = 1,
            interval = 1,
            scans = 0,
        }
    end
    local originX
    local originY
    local function processBuilding(building)
        local key = buildingKey(building)
        if not key or seen[key] == true then return end
        seen[key] = true
        local recordBefore = data.buildings[key]
        local claimed, result = claimBuilding(building, config, data)
        local source = deferredRescan == true and "LoadChunk-rescan"
            or "LoadChunk"
        local chunkName = chunkWX and chunkWY
            and (tostring(chunkWX) .. "," .. tostring(chunkWY)) or nil
        if claimed then
            pendingChunkClaims[key] = nil
            captured = captured + 1
            logBuildingResult("CLAIMED", source, building,
                data.buildings[key], chunkName)
        elseif result == "nullified" then
            pendingChunkClaims[key] = nil
            removed = removed + 1
            logBuildingResult("NULLIFIED", source, building,
                recordBefore, chunkName)
        elseif result == "partially_streamed" then
            -- LoadChunk discovered this candidate, but one or more overlapping
            -- chunks are not visible through BuildingDef:isFullyStreamedIn()
            -- yet. Keep retry authority tied to this LoadChunk discovery.
            if pendingChunkClaims[key] == nil then queued = queued + 1 end
            pendingChunkClaims[key] = building
        end
    end

    for z = chunk:getMinLevel(), chunk:getMaxLevel() do
        for x = 0, 7 do
            for y = 0, 7 do
                local square = chunk:getGridSquare(x, y, z)
                if square and originX == nil then
                    originX = square:getX() - x
                    originY = square:getY() - y
                    chunkWX = math.floor(originX / 8)
                    chunkWY = math.floor(originY / 8)
                end
                local isoBuilding = square and square:getBuilding() or nil
                local building = isoBuilding and isoBuilding:getDef() or nil
                processBuilding(building)
            end
        end
    end
    if originX and originY then
        chunkWX = math.floor(originX / 8)
        chunkWY = math.floor(originY / 8)
    end

    -- Mirror IsoChunk.doLoadGridsquare(). Its expanded BuildingDef query
    -- catches buildings whose final overlapping border chunk contains no
    -- building square. A square-only scan would never revisit those
    -- definitions once isFullyStreamedIn() becomes true.
    local world = getWorld and getWorld() or nil
    local metaGrid = world and world:getMetaGrid() or nil
    if originX and metaGrid and ArrayList then
        local buildings = ArrayList.new()
        metaGrid:getBuildingsIntersecting(
            originX - 1, originY - 1, 10, 10, buildings)
        for i = 0, buildings:size() - 1 do
            processBuilding(buildings:get(i))
        end
    end

    if captured > 0 then
        print("[TGSRR Alarms] Claimed " .. tostring(captured)
            .. " surviving vanilla alarms from a loaded chunk.")
    end
    if removed > 0 then
        print("[TGSRR Alarms] LoadChunk validation removed "
            .. tostring(removed) .. " vanilla-nullified alarms.")
    end
    if captured > 0 or removed > 0 or queued > 0 then recordsChanged() end
    return true, captured
end

local function processPendingChunkRescans()
    for key, entry in pairs(pendingChunkRescans) do
        entry.delay = entry.delay - 1
        if entry.delay <= 0 then
            Runtime.onLoadChunk(entry.chunk, true)
            entry.scans = entry.scans + 1
            if entry.scans >= CHUNK_RESCAN_LIMIT then
                pendingChunkRescans[key] = nil
            else
                entry.interval = entry.interval * 2
                entry.delay = entry.interval
            end
        end
    end
end

local function processPendingChunkClaims()
    if not authoritative() then return end
    local config = configuration()
    if not config.enabled then
        pendingChunkClaims = {}
        return
    end

    local data = root()
    local claimedCount = 0
    local removedCount = 0
    for key, building in pairs(pendingChunkClaims) do
        local record = data.buildings[key]
        if not record or record.pending ~= true then
            pendingChunkClaims[key] = nil
        else
            local recordBefore = record
            local claimed, result = claimBuilding(building, config, data)
            if claimed then
                pendingChunkClaims[key] = nil
                claimedCount = claimedCount + 1
                logBuildingResult("CLAIMED", "deferred-validation",
                    building, data.buildings[key])
            elseif result == "nullified" then
                pendingChunkClaims[key] = nil
                removedCount = removedCount + 1
                logBuildingResult("NULLIFIED", "deferred-validation",
                    building, recordBefore)
            elseif result ~= "partially_streamed" then
                pendingChunkClaims[key] = nil
            end
        end
    end

    if claimedCount > 0 then
        print("[TGSRR Alarms] Deferred LoadChunk validation claimed "
            .. tostring(claimedCount) .. " surviving vanilla alarms.")
    end
    if removedCount > 0 then
        print("[TGSRR Alarms] Deferred LoadChunk validation removed "
            .. tostring(removedCount) .. " vanilla-nullified alarms.")
    end
    if claimedCount > 0 or removedCount > 0 then recordsChanged() end
end

function Runtime.clearSpawnBuilding(player, square)
    if not authoritative() then return false, "not_authoritative" end

    square = square or (player and player:getCurrentSquare()) or nil
    local isoBuilding = square and square:getBuilding() or nil
    local building = isoBuilding and isoBuilding:getDef() or nil
    if not building then return false, "no_building" end

    local key = buildingKey(building)
    if key then root().buildings[key] = nil end
    building:setAlarmed(false)
    recordsChanged()

    logBuildingResult("EXCLUDED", "starting-building", building, nil)
    return true
end

local function roomDefFor(building, preferredRoom)
    if preferredRoom and preferredRoom.getRoomDef then
        return preferredRoom:getRoomDef()
    end
    if building and building.getFirstRoom then
        return building:getFirstRoom()
    end
    return nil
end

local function forceVanillaAlarm(building, roomDef)
    local manager = getAmbientStreamManager and getAmbientStreamManager() or nil
    if not manager or not roomDef then return false end

    local oldModifier = SandboxVars and SandboxVars.ElecShutModifier
    local age = worldAgeDays()
    local needsPowerOverride = age > integer(oldModifier, -1)

    building:setAlarmed(true)
    if needsPowerOverride then
        setElectricityShutoffDay(math.ceil(age) + 1)
    end

    local ok, message = pcall(function()
        manager:doAlarm(roomDef)
    end)

    if needsPowerOverride and oldModifier ~= nil then
        setElectricityShutoffDay(oldModifier)
    end
    building:setAlarmed(false)

    if not ok then
        print("[TGSRR Alarms] Alarm trigger failed: " .. tostring(message))
    end
    return ok
end

function Runtime.tryTrigger(building, preferredRoom, cause, triggerSquare)
    if not authoritative() or not ChallengeContext.isActive()
            or not configuration().enabled or not building then
        return false
    end

    local record = recordFor(building)
    if not isLive(record, worldAgeDays()) then return false end

    -- Mark first. If the event call fails, it must not repeatedly fire every
    -- player update and flood the console or sound system.
    record.triggered = true
    recordsChanged()
    local roomDef = roomDefFor(building, preferredRoom)
    local fired = forceVanillaAlarm(building, roomDef)
    if fired then
        local x = triggerSquare and triggerSquare:getX() or "unknown"
        local y = triggerSquare and triggerSquare:getY() or "unknown"
        local z = triggerSquare and triggerSquare:getZ() or "unknown"
        logBuildingResult("TRIGGERED", "custom-decay", building, record, nil,
            "cause=" .. tostring(cause or "unknown")
                .. " triggerAt=" .. tostring(x) .. "," .. tostring(y)
                .. "," .. tostring(z))
    end
    return fired
end

function Runtime.listRecords()
    local records = {}
    for key, record in pairs(root().buildings) do
        records[#records + 1] = {
            key = key,
            x = record.x,
            y = record.y,
            z = record.z,
            x1 = record.x1,
            y1 = record.y1,
            x2 = record.x2,
            y2 = record.y2,
            expiryDay = record.expiryDay,
            pending = record.pending == true,
            triggered = record.triggered == true,
            live = isLive(record, worldAgeDays()),
        }
    end
    table.sort(records, function(a, b)
        if a.pending ~= b.pending then return a.pending == true end
        if a.triggered ~= b.triggered then return not a.triggered end
        return tostring(a.key) < tostring(b.key)
    end)
    return records
end

function Runtime.listDebugRecords()
    local data = root()
    -- Debug-only geometry refresh. This lets the browser measure against the
    -- whole BuildingDef instead of whichever room happened to be stored as
    -- the alarm's teleport anchor.
    forEachBuilding(function(building)
        local record = data.buildings[buildingKey(building)]
        if record then setRecordPosition(record, building) end
    end)
    return Runtime.listRecords()
end

function Runtime.currentBuildingKey(player)
    local square = player and player:getCurrentSquare() or nil
    local isoBuilding = square and square:getBuilding() or nil
    local building = isoBuilding and isoBuilding:getDef() or nil
    return building and buildingKey(building) or nil
end

function Runtime.getRecordRevision()
    return recordRevision
end

function Runtime.inspectRecord(key)
    key = tostring(key)
    local data = root()
    local record = data.buildings[key]
    local building
    if record then
        building = buildingByKey(key, record)
        if building then setRecordPosition(record, building) end
    end
    if not record then return nil end
    local loadedChunks, totalChunks, missingChunks, chunkDiagnostic =
        chunkStreamingDetails(building)
    return {
        key = key,
        x = record.x,
        y = record.y,
        z = record.z,
        x1 = record.x1,
        y1 = record.y1,
        x2 = record.x2,
        y2 = record.y2,
        expiryDay = record.expiryDay,
        pending = record.pending == true,
        triggered = record.triggered == true,
        live = isLive(record, worldAgeDays()),
        queued = pendingChunkClaims[key] ~= nil,
        fullyStreamed = building and building.isFullyStreamedIn
            and building:isFullyStreamedIn() or false,
        vanillaAlarmed = building and building:isAlarmed() or false,
        loadedChunks = loadedChunks,
        totalChunks = totalChunks,
        missingChunks = missingChunks,
        chunkDiagnostic = chunkDiagnostic,
    }
end

function Runtime.recordExists(key)
    return root().buildings[tostring(key)] ~= nil
end

function Runtime.debugReset(key, live)
    if not authoritative() then return false end
    local record = root().buildings[tostring(key)]
    if not record or record.pending == true then return false end

    record.triggered = false
    if live == true then
        record.expiryDay = math.ceil(worldAgeDays()) + 1
    elseif live == false then
        record.expiryDay = math.floor(worldAgeDays()) - 1
    end

    local building = buildingByKey(tostring(key))
    if building then building:setAlarmed(false) end
    recordsChanged()
    return true
end

function Runtime.debugTrigger(key)
    local building = buildingByKey(tostring(key))
    local room = building and building:getFirstRoom() or nil
    local square = room and getCell():getGridSquare(
        room:getX(), room:getY(), room:getZ()) or nil
    if not square then return false end
    return building and Runtime.tryTrigger(
        building, nil, "debug-ui", square) or false
end

function Runtime.debugGridOnline()
    return debugOriginalElecModifier ~= nil
end

function Runtime.debugToggleGrid()
    if not authoritative() then return false, "not_authoritative" end
    if debugOriginalElecModifier ~= nil then
        local original = debugOriginalElecModifier
        debugOriginalElecModifier = nil
        setElectricityShutoffDay(original)
        print("[TGSRR Alarms] Debug electricity override restored to day "
            .. tostring(original) .. ".")
        return false, original
    end

    debugOriginalElecModifier = powerShutoffDay()
    local forced = math.ceil(worldAgeDays()) + 1
    setElectricityShutoffDay(forced)
    print("[TGSRR Alarms] Debug electricity override enabled through day "
        .. tostring(forced) .. ".")
    return true, forced
end

local function restoreDebugGrid()
    if debugOriginalElecModifier == nil then return end
    local original = debugOriginalElecModifier
    debugOriginalElecModifier = nil
    setElectricityShutoffDay(original)
end

local function roomZombieCount(room)
    if not room or not room.getSquares or not instanceof then return nil end
    local squares = room:getSquares()
    if not squares then return nil end
    local count = 0
    for i = 0, squares:size() - 1 do
        local square = squares:get(i)
        local moving = square and square:getMovingObjects() or nil
        if moving then
            for j = 0, moving:size() - 1 do
                if instanceof(moving:get(j), "IsoZombie") then
                    count = count + 1
                end
            end
        end
    end
    return count
end

local function reconcileRoomNullifiers()
    for building, state in pairs(pendingRoomNullifiers) do
        pendingRoomNullifiers[building] = nil
        local key = state.key
        local record = root().buildings[key]
        if record and record.triggered ~= true then
            local after = roomZombieCount(state.room)
            local populated = state.before ~= nil and after ~= nil
                and after > state.before
            if populated or (state.before == nil and not building:isAlarmed()) then
                root().buildings[key] = nil
                recordsChanged()
                logBuildingResult("NULLIFIED", "room-population",
                    building, record)
            end
        end
    end
end

function Runtime.onSeeNewRoom(room)
    if not authoritative() or not ChallengeContext.isActive()
            or not configuration().enabled or not room then
        return
    end
    local isoBuilding = room:getBuilding()
    local building = isoBuilding and isoBuilding:getDef() or nil
    local key = buildingKey(building)
    local record = key and root().buildings[key] or nil
    if record and record.pending ~= true and record.triggered ~= true then
        -- IsoCell calls VirtualZombieManager.roomSpotted() immediately after
        -- this event. Compare the room's zombie count afterwards so an alarm
        -- already owned through LoadChunk still receives vanilla's population
        -- nullifier.
        pendingRoomNullifiers[building] = {
            key = key,
            room = room,
            before = roomZombieCount(room),
        }
    end
end

local function onPlayerUpdate(player)
    if not ChallengeContext.isActive() then return end
    reconcileRoomNullifiers()
    if not player then return end
    local square = player:getCurrentSquare()
    local room = square and square:getRoom() or nil
    local isoBuilding = square and square:getBuilding() or nil
    local definition = isoBuilding and isoBuilding:getDef() or nil
    if definition then
        if player.isInvisible and player:isInvisible() then return end
        if player.isGhostMode and player:isGhostMode() then return end
        Runtime.tryTrigger(definition, room, "player-inside", square)
    end
end

local function definitionAt(square)
    local room = square and square:getRoom() or nil
    local building = room and room:getBuilding() or nil
    return building and building:getDef() or nil, room
end

local function triggerBesideWindow(window, cause)
    local square = window and window:getSquare() or nil
    if not square then return end

    local indoorSquare = window.getIndoorSquare and window:getIndoorSquare()
        or nil
    local candidates = {}
    if indoorSquare then candidates[#candidates + 1] = indoorSquare end
    local nearby = {
        square,
        getCell():getGridSquare(square:getX() - 1, square:getY(), square:getZ()),
        getCell():getGridSquare(square:getX() + 1, square:getY(), square:getZ()),
        getCell():getGridSquare(square:getX(), square:getY() - 1, square:getZ()),
        getCell():getGridSquare(square:getX(), square:getY() + 1, square:getZ()),
    }
    for i = 1, 5 do
        if nearby[i] then candidates[#candidates + 1] = nearby[i] end
    end
    for i = 1, #candidates do
        local definition, room = definitionAt(candidates[i])
        if definition and recordFor(definition) then
            Runtime.tryTrigger(definition, room, cause, square)
            return
        end
    end
end

local pendingWindowChanges = {}
local WINDOW_WATCH_TIMEOUT_TICKS = 3600

local function alarmHitDebugEnabled()
    return isDebugEnabled and isDebugEnabled()
end

local function alarmHitDetails(target, character, weapon)
    local square = target and target.getSquare and target:getSquare() or nil
    local indoor = target and target.getIndoorSquare
        and target:getIndoorSquare() or nil
    local isoBuilding = indoor and indoor:getBuilding()
        or (square and square:getBuilding()) or nil
    local building = isoBuilding and isoBuilding:getDef() or nil
    local targetType = "other"
    if instanceof and target then
        if instanceof(target, "IsoWindow") then
            targetType = "IsoWindow"
        elseif instanceof(target, "IsoBarricade") then
            targetType = "IsoBarricade"
        elseif instanceof(target, "IsoThumpable") then
            targetType = "IsoThumpable"
        end
    end
    local actor = "unknown"
    if character then
        actor = character.isZombie and character:isZombie()
            and "zombie" or "player"
    end
    local weaponName = weapon and weapon.getFullType
        and weapon:getFullType() or "none"
    return "targetType=" .. targetType
        .. " objectName=" .. tostring(target and target.getObjectName
            and target:getObjectName() or "unknown")
        .. " at=" .. tostring(square and square:getX() or "unknown")
        .. "," .. tostring(square and square:getY() or "unknown")
        .. "," .. tostring(square and square:getZ() or "unknown")
        .. " building=" .. tostring(buildingKey(building) or "none")
        .. " actor=" .. actor .. " weapon=" .. tostring(weaponName)
end

local function logAlarmHit(stage, target, character, weapon, decision)
    if not alarmHitDebugEnabled() then return end
    print("[TGSRR Alarms] HIT stage=" .. tostring(stage) .. " "
        .. alarmHitDetails(target, character, weapon)
        .. " decision=" .. tostring(decision))
end

local function watchWindow(window, condition, character,
        requiresSmashSuccess)
    if not window then return end
    local conditions = pendingWindowChanges[window]
    if not conditions then
        conditions = {}
        pendingWindowChanges[window] = conditions
    end

    -- Repeated or overlapping action hooks refresh one watcher rather than
    -- retaining duplicate references to the same Java window object.
    conditions[condition] = 0
    conditions[condition .. "Character"] = character
    if condition == "destroyed" then
        conditions.destroyedRequiresSmashSuccess =
            requiresSmashSuccess == true
        conditions.destroyedSmashSucceeded = nil
    end
end

local function watchDirectCombatWindow(window, character)
    if not window then return end
    local conditions = pendingWindowChanges[window]
    if not conditions then
        conditions = {}
        pendingWindowChanges[window] = conditions
    end
    conditions.directCombat = true
    conditions.directCombatCharacter = character
end

local function patchWindowActions()
    if not authoritative() then return end

    require("TimedActions/ISOpenCloseWindow")
    local openClose = ISOpenCloseWindow
    if openClose then
        local original = openClose.TGSRRCustomAlarmOriginalPerform
            or openClose.perform
        openClose.TGSRRCustomAlarmOriginalPerform = original
        openClose.perform = function(self)
            local wasOpen = self.object and self.object:IsOpen()
            local result = original(self)
            if self.object and not wasOpen then
                watchWindow(self.object, "open", self.character)
            end
            return result
        end
    end

    require("TimedActions/ISSmashWindow")
    local smash = ISSmashWindow
    if smash then
        local originalStart = smash.TGSRRCustomAlarmOriginalStart
            or smash.start
        smash.TGSRRCustomAlarmOriginalStart = originalStart
        smash.start = function(self)
            local window = self.window or self.object
            local wasDestroyed = window and window:isDestroyed()
            local result = originalStart(self)
            if window and not wasDestroyed then
                -- Vanilla sets OwnerSmashedIt only at the animation's actual
                -- AttackCollisionCheck. A cancelled action may leave this
                -- watcher briefly, but can never satisfy the success gate.
                watchWindow(window, "destroyed", self.character, true)
                logAlarmHit("smash-action", window, self.character, nil,
                    "watch-vanilla-success")
            end
            return result
        end
    end

    if not isServer or not isServer() then
        require("ISUI/ISButtonPrompt")
        if ISButtonPrompt then
            local originalOpen =
                ISButtonPrompt.TGSRRCustomAlarmOriginalOpenWindow
                or ISButtonPrompt.openWindow
            ISButtonPrompt.TGSRRCustomAlarmOriginalOpenWindow = originalOpen
            ISButtonPrompt.openWindow = function(self, window)
                local wasOpen = window and window:IsOpen()
                local player = getSpecificPlayer(self.player)
                local result = originalOpen(self, window)
                if window and not wasOpen then
                    watchWindow(window, "open", player)
                end
                return result
            end
        end
    end
end

local function onWeaponHitThumpable(character, weapon, target)
    if not authoritative() or not target or not instanceof then return end
    if not instanceof(target, "IsoWindow") then
        logAlarmHit("received", target, character, weapon,
            "ignored-non-window")
        return
    end
    if character and character.isZombie and character:isZombie()
            and not (SandboxVars and SandboxVars.ZombieLore
                and SandboxVars.ZombieLore.TriggerHouseAlarm) then
        local conditions = pendingWindowChanges[target]
        if conditions then
            conditions.destroyed = nil
            conditions.destroyedCharacter = nil
            conditions.destroyedRequiresSmashSuccess = nil
            conditions.destroyedSmashSucceeded = nil
        end
        logAlarmHit("received", target, character, weapon,
            "ignored-zombie-lore")
        return
    end
    if target:isDestroyed() then
        logAlarmHit("received", target, character, weapon,
            "ignored-already-destroyed")
        return
    end
    logAlarmHit("received", target, character, weapon,
        "watch-destruction")
    watchWindow(target, "destroyed", character, false)
end

local function onWeaponSwingHitPoint(character, weapon)
    if not authoritative() or not ChallengeContext.isActive()
            or not character or not instanceof then return end
    if character.isZombie and character:isZombie() then return end

    local square = character:getSquare()
    if not square then return end
    local cell = square:getCell()
    if not cell then return end

    -- CombatManager.processIsoWindow() directly calls smashWindow() for a
    -- window stored in HitInfo. That vanilla route triggers handleAlarm(),
    -- but bypasses WeaponHit() and OnWeaponHitThumpable. HitInfo is not
    -- explicitly exposed by LuaManager, so snapshot the small set of intact
    -- windows that the adjacent melee collision can reach. Only the window
    -- vanilla actually destroys will satisfy the watcher.
    for x = square:getX() - 1, square:getX() + 1 do
        for y = square:getY() - 1, square:getY() + 1 do
            local nearby = cell:getGridSquare(x, y, square:getZ())
            local objects = nearby and nearby:getSpecialObjects() or nil
            if objects then
                for index = 0, objects:size() - 1 do
                    local object = objects:get(index)
                    if object and instanceof(object, "IsoWindow")
                            and not object:isDestroyed() then
                        watchDirectCombatWindow(object, character)
                        logAlarmHit("melee-snapshot", object, character,
                            weapon, "watch-direct-combat")
                    end
                end
            end
        end
    end
end

local function inspectWindowChanges()
    if not ChallengeContext.isActive() then return end
    processPendingChunkRescans()
    processPendingChunkClaims()
    reconcileRoomNullifiers()
    for window, conditions in pairs(pendingWindowChanges) do
        if conditions.directCombat then
            local character = conditions.directCombatCharacter
            conditions.directCombat = nil
            conditions.directCombatCharacter = nil
            -- CombatManager.processIsoWindow() runs synchronously after
            -- OnWeaponSwingHitPoint. Inspect exactly once on the following
            -- tick, then discard the candidate so a later zombie smash
            -- cannot be attributed to this player attack.
            if window:isDestroyed() then
                logAlarmHit("resolved", window, character, nil,
                    "destroyed-by-direct-combat")
                triggerBesideWindow(window,
                    "window-destroyed direct-combat")
            else
                logAlarmHit("resolved", window, character, nil,
                    "direct-combat-no-destruction")
            end
        end

        local openTicks = conditions.open
        if openTicks ~= nil then
            if window:IsOpen() then
                local character = conditions.openCharacter
                local outcome = character and character.getVariableString
                    and character:getVariableString("OpenWindowOutcome") or nil
                conditions.open = nil
                conditions.openCharacter = nil
                -- Vanilla opens the window and calls its alarm from the
                -- successful OpenWindowState animation event. Ignore state
                -- changes caused later by another actor.
                if outcome == "success" then
                    triggerBesideWindow(window,
                        "window-open watcherTicks=" .. tostring(openTicks))
                end
            elseif openTicks >= WINDOW_WATCH_TIMEOUT_TICKS then
                conditions.open = nil
                conditions.openCharacter = nil
            else
                conditions.open = openTicks + 1
            end
        end

        local destroyedTicks = conditions.destroyed
        if destroyedTicks ~= nil then
            local character = conditions.destroyedCharacter
            if character and character.getVariableBoolean
                    and character:getVariableBoolean("OwnerSmashedIt") then
                -- SmashWindowState clears OwnerSmashedIt when it exits. Keep
                -- the successful collision observed during the action.
                conditions.destroyedSmashSucceeded = true
            end
            if window:isDestroyed() then
                local requiresSuccess =
                    conditions.destroyedRequiresSmashSuccess == true
                local smashedByOwner =
                    conditions.destroyedSmashSucceeded == true
                conditions.destroyed = nil
                conditions.destroyedCharacter = nil
                conditions.destroyedRequiresSmashSuccess = nil
                conditions.destroyedSmashSucceeded = nil
                if not requiresSuccess or smashedByOwner then
                    logAlarmHit("resolved", window, character, nil,
                        "destroyed-after-" .. tostring(destroyedTicks)
                            .. "-ticks")
                    triggerBesideWindow(window,
                        "window-destroyed watcherTicks="
                            .. tostring(destroyedTicks))
                else
                    logAlarmHit("resolved", window, character, nil,
                        "ignored-without-vanilla-smash-success")
                end
            elseif destroyedTicks >= WINDOW_WATCH_TIMEOUT_TICKS then
                local character = conditions.destroyedCharacter
                conditions.destroyed = nil
                conditions.destroyedCharacter = nil
                conditions.destroyedRequiresSmashSuccess = nil
                conditions.destroyedSmashSucceeded = nil
                logAlarmHit("resolved", window, character, nil,
                    "timeout-not-destroyed")
            else
                conditions.destroyed = destroyedTicks + 1
            end
        end

        if conditions.open == nil and conditions.destroyed == nil
                and conditions.directCombat == nil then
            pendingWindowChanges[window] = nil
        end
    end
end

local function clearWindowChanges()
    pendingWindowChanges = {}
    pendingRoomNullifiers = {}
    pendingChunkClaims = {}
    pendingChunkRescans = {}
    restoreDebugGrid()
end

Runtime.configuration = configuration
Runtime.expiryDay = expiryDay
Runtime.isLive = isLive
Runtime.reconcileRoomNullifiers = reconcileRoomNullifiers
Runtime.processPendingChunkClaims = processPendingChunkClaims
Runtime.processPendingChunkRescans = processPendingChunkRescans

Events.OnLoadedMapZones.Add(Runtime.capture)
if Events.OnNewGame then
    Events.OnNewGame.Add(Runtime.clearSpawnBuilding)
end
Events.OnGameStart.Add(Runtime.capture)
Events.OnGameStart.Add(patchWindowActions)
Events.LoadChunk.Add(Runtime.onLoadChunk)
if Events.OnSeeNewRoom then Events.OnSeeNewRoom.Add(Runtime.onSeeNewRoom) end
Events.OnPlayerUpdate.Add(onPlayerUpdate)
if Events.OnWeaponHitThumpable then
    Events.OnWeaponHitThumpable.Add(onWeaponHitThumpable)
end
if Events.OnWeaponSwingHitPoint then
    Events.OnWeaponSwingHitPoint.Add(onWeaponSwingHitPoint)
end
if Events.OnTick then Events.OnTick.Add(inspectWindowChanges) end
if Events.OnMainMenuEnter then
    Events.OnMainMenuEnter.Add(clearWindowChanges)
end

return Runtime
