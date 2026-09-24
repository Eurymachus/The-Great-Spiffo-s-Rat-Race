local RanchControl = require("TGSRR/Animals/RanchControl")
local RanchSpawner = require("TGSRR/Animals/RanchSpawner")
local RanchMortality = require("TGSRR/Animals/RanchMortality")

local Runtime = {}

local MOD_DATA_KEY = "TGSRR_RanchControl"
local SCHEMA_VERSION = 1
local CONTROLLED_NAME_PREFIX = "[TGSRR] "
local ranches = {}
local ranchGroups = {}
local readyConfirmed = {}
local initialized = false

local function authoritative()
    return not (isClient and isClient())
end

local function controlledName(name)
    name = name or "Ranch"
    if name:sub(1, #CONTROLLED_NAME_PREFIX) == CONTROLLED_NAME_PREFIX then
        return name
    end
    return CONTROLLED_NAME_PREFIX .. name
end

local function unprefixedName(name)
    name = name or "Ranch"
    if name:sub(1, #CONTROLLED_NAME_PREFIX) == CONTROLLED_NAME_PREFIX then
        return name:sub(#CONTROLLED_NAME_PREFIX + 1)
    end
    return name
end

local function worldAgeHours()
    local gameTime = getGameTime and getGameTime() or nil
    return gameTime and gameTime:getWorldAgeHours() or nil
end

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
        data.ranches = {}
    elseif type(data.ranches) ~= "table" then
        data.ranches = {}
    end
    return data
end

local function persistedRecord(key, entry)
    local data = root()
    local record = data.ranches[key]
    local created = false
    if type(record) ~= "table" then
        local zone = entry.zone
        record = {
            name = entry.originalName,
            x = zone:getX(),
            y = zone:getY(),
            z = zone:getZ(),
            width = zone:getWidth(),
            height = zone:getHeight(),
            interceptedAt = worldAgeHours(),
            ready = false,
        }
        data.ranches[key] = record
        created = true
    end
    return record, created
end

local function wasProcessedByVanilla(zone)
    if not zone or not zone.getHoursSinceLastSeen then return false end

    local now = worldAgeHours()
    local hoursSince = tonumber(zone:getHoursSinceLastSeen())
    if not now or not hoursSince then return false end

    return now - hoursSince >= 0.5
end

local function findDesignation(zone)
    local zones = DesignationZone.getAllZonesByType("AnimalZone")
    for i = 0, zones:size() - 1 do
        local existing = zones:get(i)
        if existing:getX() == zone:getX()
                and existing:getY() == zone:getY()
                and existing:getZ() == zone:getZ()
                and existing:getW() == zone:getWidth()
                and existing:getH() == zone:getHeight() then
            return existing
        end
    end
    return nil
end

local function ensureDesignation(entry, allowCreate)
    local zone = entry.zone
    local designation = findDesignation(zone)
    if designation then return designation, false end
    if allowCreate ~= true then return nil, false end

    designation = DesignationZoneAnimal.new(
        controlledName("Ranch"),
        zone:getX(),
        zone:getY(),
        zone:getZ(),
        zone:getX() + zone:getWidth(),
        zone:getY() + zone:getHeight(),
        true)

    return designation, designation ~= nil
end

local function inheritDesignation(designation, existing, record, prefixName)
    if not designation or not existing then return false end

    local inheritedName = unprefixedName(existing:getName())
    local desiredName = prefixName
        and controlledName(inheritedName) or inheritedName
    if designation:getName() ~= desiredName then
        designation:setName(desiredName)
    end
    record.spawnProcessed = true
    record.spawnInheritedExistingDesignation = true
    record.designationName = inheritedName
    record.spawnedFemales = 0
    record.spawnedMales = 0
    record.spawnedBabies = 0
    return true
end

local function inheritConnectedDesignation(designation, record)
    if not designation or not DesignationZoneAnimal
            or not DesignationZoneAnimal.getAllDZones then
        return false
    end

    local connected = DesignationZoneAnimal.getAllDZones(
        nil, designation, nil)
    if not connected then return false end

    for i = 0, connected:size() - 1 do
        local existing = connected:get(i)
        if existing ~= designation then
            return inheritDesignation(designation, existing, record, true)
        end
    end

    return false
end

local function spawnedTotal(record)
    return (tonumber(record.spawnedFemales) or 0)
        + (tonumber(record.spawnedMales) or 0)
        + (tonumber(record.spawnedBabies) or 0)
end

local function updateDesignationName(designation, record)
    if not designation then return end

    local desiredName = "Ranch"
    if (not record.spawnGlobalName or record.spawnGlobalName == "")
            and record.spawnDefinition
            and RanchZoneDefinitions
            and RanchZoneDefinitions.type then
        local definition =
            RanchZoneDefinitions.type[record.spawnDefinition]
        record.spawnGlobalName =
            type(definition) == "table" and definition.globalName or nil
    end
    if record.spawnProcessed == true
            and record.designationName
            and record.designationName ~= ""
            and record.designationName ~= "Ranch" then
        desiredName = record.designationName
    elseif record.spawnProcessed == true and spawnedTotal(record) > 0
            and record.spawnGlobalName and record.spawnGlobalName ~= "" then
        if not record.designationName
                or record.designationName == ""
                or record.designationName == "Ranch" then
            local suffix = ZombRand(10000)
            local animalName = getText(
                "IGUI_AnimalType_Global_" .. record.spawnGlobalName)
            record.designationName =
                getText("UI_Ranch", animalName, suffix)
        end
        desiredName = record.designationName
    else
        record.designationName = "Ranch"
    end

    if record.designationCreatedByTGSRR == true then
        desiredName = controlledName(desiredName)
    else
        desiredName = unprefixedName(desiredName)
    end
    if designation:getName() ~= desiredName then
        designation:setName(desiredName)
    end
end

Runtime.updateDesignationName = updateDesignationName

local function intervalsOverlap(a1, a2, b1, b2)
    return math.max(a1, b1) < math.min(a2, b2)
end

local function zonesConnected(first, second)
    local a = first.zone
    local b = second.zone
    if a:getZ() ~= b:getZ() then return false end

    local ax1, ay1 = a:getX(), a:getY()
    local ax2 = ax1 + a:getWidth()
    local ay2 = ay1 + a:getHeight()
    local bx1, by1 = b:getX(), b:getY()
    local bx2 = bx1 + b:getWidth()
    local by2 = by1 + b:getHeight()

    return ((ay2 == by1 or by2 == ay1)
            and intervalsOverlap(ax1, ax2, bx1, bx2))
        or ((ax2 == bx1 or bx2 == ax1)
            and intervalsOverlap(ay1, ay2, by1, by2))
end

local function buildGroups()
    ranchGroups = {}
    local assigned = {}

    for key, entry in pairs(ranches) do
        if not assigned[key] then
            local group = {}
            local queue = { key }
            assigned[key] = true
            local cursor = 1

            while cursor <= #queue do
                local currentKey = queue[cursor]
                cursor = cursor + 1
                group[#group + 1] = currentKey

                for candidateKey, candidate in pairs(ranches) do
                    if not assigned[candidateKey]
                            and zonesConnected(
                                ranches[currentKey], candidate) then
                        assigned[candidateKey] = true
                        queue[#queue + 1] = candidateKey
                    end
                end
            end

            table.sort(group)
            for i = 1, #group do
                ranchGroups[group[i]] = group
            end
        end
    end
end

local function propagateGroupResult(key, source)
    local group = ranchGroups[key] or { key }
    for i = 1, #group do
        local memberKey = group[i]
        if memberKey ~= key then
            local member = persistedRecord(
                memberKey, ranches[memberKey])
            if member.spawnProcessedBeforeInstall ~= true then
                member.spawnProcessed = true
                member.spawnInheritedFrom = key
                member.spawnChance = source.spawnChance
                member.spawnSkippedByChance =
                    source.spawnSkippedByChance == true
                member.spawnDefinition = source.spawnDefinition
                member.spawnGlobalName = source.spawnGlobalName
                member.designationName =
                    source.designationName or "Ranch"
                member.spawnedFemales = 0
                member.spawnedMales = 0
                member.spawnedBabies = 0
            end
        end
    end
end

function Runtime.intercept(metaGrid)
    if not authoritative() then return 0, 0 end

    local discoveredCount
    ranches, discoveredCount = RanchControl.intercept(metaGrid)
    buildGroups()
    readyConfirmed = {}
    initialized = true

    local count = 0
    local newlyIntercepted = 0
    local processedBeforeInstall = 0
    for key, entry in pairs(ranches) do
        count = count + 1
        if entry.wasVanilla then newlyIntercepted = newlyIntercepted + 1 end
        local record, created = persistedRecord(key, entry)
        if created and wasProcessedByVanilla(entry.zone) then
            processedBeforeInstall = processedBeforeInstall + 1
            record.spawnProcessed = true
            record.spawnProcessedBeforeInstall = true
            record.spawnedFemales = 0
            record.spawnedMales = 0
            record.spawnedBabies = 0
        end
    end

    print("[TGSRR Ranch] Interception active: controlled=" .. tostring(count)
        .. ", newly relabelled=" .. tostring(newlyIntercepted)
        .. ", vanilla type=" .. RanchControl.VANILLA_TYPE
        .. ", controlled type=" .. RanchControl.CONTROLLED_TYPE)

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Ranch] DEBUG: ranches discovered="
            .. tostring(discoveredCount or 0)
            .. ", vanilla processed inferred="
            .. tostring(processedBeforeInstall))
    end

    return count, newlyIntercepted
end

function Runtime.onLoadedMapZones()
    if not authoritative() then return end
    local world = getWorld and getWorld() or nil
    local metaGrid = world and world:getMetaGrid() or nil
    if not metaGrid then
        print("[TGSRR Ranch] ERROR: meta-grid unavailable at OnLoadedMapZones")
        return
    end

    local mortality = RanchMortality.configuration()
    if mortality.enabled ~= true then
        local restored = RanchControl.restoreVanilla(metaGrid)
        ranches = {}
        ranchGroups = {}
        readyConfirmed = {}
        initialized = false
        print("[TGSRR Ranch] Custom ranch mortality disabled; "
            .. "vanilla ranch handling active, restored="
            .. tostring(restored))
        return
    end

    print("[TGSRR Ranch] Scanning loaded meta-cells for ranch zones...")
    Runtime.intercept(metaGrid)
end

function Runtime.onLoadChunk()
    if not authoritative() or not initialized then return end

    for key, entry in pairs(ranches) do
        local zone = entry.zone
        local record = persistedRecord(key, entry)
        if readyConfirmed[key] ~= true and zone:isFullyStreamed() then
            local controlled =
                zone:getType() == RanchControl.CONTROLLED_TYPE
            local designation, designationCreated =
                ensureDesignation(entry, record.spawnProcessed ~= true)
            readyConfirmed[key] = true
            record.ready = true
            record.readyAt = worldAgeHours()
            record.confirmedControlledType = controlled
            record.designationAvailable = designation ~= nil
            if record.designationCreatedByTGSRR == nil
                    and record.designationCreated == true then
                record.designationCreatedByTGSRR = true
            end
            if designationCreated == true then
                record.designationCreatedByTGSRR = true
            elseif record.designationCreatedByTGSRR == nil then
                record.designationCreatedByTGSRR = false
            end
            record.designationCreated = designationCreated == true

            if designation
                    and designationCreated ~= true
                    and (record.spawnProcessed ~= true
                        or record.spawnProcessedBeforeInstall == true) then
                inheritDesignation(designation, designation, record, false)
            end

            if record.spawnProcessed ~= true then
                inheritConnectedDesignation(designation, record)
            end

            if record.spawnProcessed ~= true then
                local setting = SandboxVars and SandboxVars.AnimalRanchChance
                record.spawnChance = RanchSpawner.ranchSpawnChance(setting)
                record.spawnRolledAt = worldAgeHours()

                if RanchSpawner.shouldPopulate(setting) then
                    local spawnResult, spawnError =
                        RanchSpawner.populate(zone, entry.originalName)
                    record.spawnError = spawnError
                    record.spawnProcessed = spawnResult ~= nil
                    record.spawnedFemales =
                        spawnResult and spawnResult.females or 0
                    record.spawnedMales =
                        spawnResult and spawnResult.males or 0
                    record.spawnedBabies =
                        spawnResult and spawnResult.babies or 0
                    record.spawnDefinition = spawnResult
                        and spawnResult.definition
                        and spawnResult.definition.type or entry.originalName
                    record.spawnGlobalName = spawnResult
                        and spawnResult.definition
                        and spawnResult.definition.globalName or nil
                else
                    record.spawnProcessed = true
                    record.spawnSkippedByChance = true
                end
            end

            if designation then
                updateDesignationName(designation, record)
            end
            if not record.spawnInheritedFrom
                    and record.spawnProcessedBeforeInstall ~= true then
                propagateGroupResult(key, record)
            end

            print("[TGSRR Ranch] CONFIRMED fully streamed: " .. key
                .. ", type=" .. tostring(zone:getType())
                .. ", vanilla suppressed=" .. tostring(controlled)
                .. ", livestock zone="
                .. tostring(designation and designation:getName() or nil)
                .. ", zone created=" .. tostring(designationCreated)
                .. ", spawned=" .. tostring(
                    (record.spawnedFemales or 0)
                    + (record.spawnedMales or 0)
                    + (record.spawnedBabies or 0))
                .. ", spawn error=" .. tostring(record.spawnError))
        end
    end
end

function Runtime.getStatus()
    return {
        initialized = initialized,
        ranches = ranches,
        persisted = root(),
    }
end

Events.OnLoadedMapZones.Add(Runtime.onLoadedMapZones)
Events.LoadChunk.Add(Runtime.onLoadChunk)

return Runtime
