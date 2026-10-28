local Exporter = {}

local OUTPUT_FILE = "TGSRR/RSLBuildingIds.ini"

local function clean(value)
    return tostring(value or ""):gsub("[\r\n]", " ")
end

local function collectRecord(metaGrid, source)
    local roomDef = metaGrid:getRoomAt(source.x, source.y, source.z)
    local buildingDef = roomDef and roomDef:getBuilding()
        or metaGrid:getBuildingAt(source.x, source.y, source.z)

    local result = {
        id = source.id,
        x = source.x,
        y = source.y,
        z = source.z,
        note = source.note,
        status = buildingDef and "resolved" or "no-building",
    }

    if roomDef then
        result.roomId = roomDef:getIDString()
        result.roomName = roomDef:getName()
    end

    if buildingDef then
        result.buildingId = buildingDef:getIDString()
        result.buildingMinX = buildingDef:getX()
        result.buildingMinY = buildingDef:getY()
        result.buildingMaxX = buildingDef:getX2()
        result.buildingMaxY = buildingDef:getY2()
    end

    return result
end

function Exporter.collect(records, metaGrid)
    local results = {}
    local resolved = 0
    local uniqueBuildings = {}

    for index, source in ipairs(records) do
        local result = collectRecord(metaGrid, source)
        results[index] = result
        if result.buildingId then
            resolved = resolved + 1
            uniqueBuildings[result.buildingId] = true
        end
    end

    local uniqueCount = 0
    for _, _ in pairs(uniqueBuildings) do
        uniqueCount = uniqueCount + 1
    end

    return results, {
        total = #records,
        resolved = resolved,
        unresolved = #records - resolved,
        uniqueBuildings = uniqueCount,
    }
end

local function writeValue(writer, key, value)
    if value ~= nil then
        writer:write(tostring(key) .. "=" .. clean(value) .. "\n")
    end
end

function Exporter.write(results, summary)
    local writer = getFileWriter(OUTPUT_FILE, true, false)
    if not writer then return false, "Could not open " .. OUTPUT_FILE end

    writer:write("[Summary]\n")
    writeValue(writer, "gameVersion", getCore():getVersionNumber())
    writeValue(writer, "total", summary.total)
    writeValue(writer, "resolved", summary.resolved)
    writeValue(writer, "unresolved", summary.unresolved)
    writeValue(writer, "uniqueBuildings", summary.uniqueBuildings)
    writer:write("\n")

    for _, result in ipairs(results) do
        writer:write("[Record." .. tostring(result.id) .. "]\n")
        writeValue(writer, "x", result.x)
        writeValue(writer, "y", result.y)
        writeValue(writer, "z", result.z)
        writeValue(writer, "note", result.note)
        writeValue(writer, "status", result.status)
        writeValue(writer, "buildingId", result.buildingId)
        writeValue(writer, "roomId", result.roomId)
        writeValue(writer, "roomName", result.roomName)
        writeValue(writer, "buildingMinX", result.buildingMinX)
        writeValue(writer, "buildingMinY", result.buildingMinY)
        writeValue(writer, "buildingMaxX", result.buildingMaxX)
        writeValue(writer, "buildingMaxY", result.buildingMaxY)
        writer:write("\n")
    end

    writer:close()
    return true
end

function Exporter.run(records)
    local world = getWorld()
    local metaGrid = world and world:getMetaGrid()
    if not metaGrid then return false, "World metadata is unavailable." end

    local results, summary = Exporter.collect(records, metaGrid)
    local ok, err = Exporter.write(results, summary)
    if not ok then return false, err end
    return true, summary
end

function Exporter.getOutputFile()
    return OUTPUT_FILE
end

return Exporter
