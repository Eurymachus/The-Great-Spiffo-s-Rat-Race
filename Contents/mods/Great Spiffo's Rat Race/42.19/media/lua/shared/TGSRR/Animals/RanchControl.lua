local RanchControl = {}

RanchControl.VANILLA_TYPE = "Ranch"
RanchControl.CONTROLLED_TYPE = "TGSRR_Ranch"
RanchControl.CELL_SIZE = 256

function RanchControl.key(zone)
    return table.concat({
        tostring(zone:getX()),
        tostring(zone:getY()),
        tostring(zone:getZ()),
        tostring(zone:getWidth()),
        tostring(zone:getHeight()),
        tostring(zone:getName() or ""),
    }, ":")
end

function RanchControl.worldBounds(metaGrid)
    local cellSize = RanchControl.CELL_SIZE
    local minCellX = metaGrid:getMinX()
    local minCellY = metaGrid:getMinY()

    return minCellX * cellSize,
        minCellY * cellSize,
        (metaGrid:getMaxX() - minCellX + 1) * cellSize,
        (metaGrid:getMaxY() - minCellY + 1) * cellSize
end

local function visitRanchZones(metaGrid, visitor)
    for cellY = metaGrid:getMinY(), metaGrid:getMaxY() do
        for cellX = metaGrid:getMinX(), metaGrid:getMaxX() do
            local cell = metaGrid:getCellData(cellX, cellY)
            if cell then
                for chunkY = 0, 31 do
                    for chunkX = 0, 31 do
                        if cell:hasChunk(chunkX, chunkY) then
                            local chunk = cell:getChunk(chunkX, chunkY)
                            for i = 0, chunk:getZonesSize() - 1 do
                                local zone = chunk:getZone(i)
                                local zoneType = zone and zone:getType()

                                if zoneType == RanchControl.VANILLA_TYPE
                                        or zoneType == RanchControl.CONTROLLED_TYPE then
                                    visitor(zone, zoneType)
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end

function RanchControl.intercept(metaGrid)
    local ranches = {}

    visitRanchZones(metaGrid, function(zone, zoneType)
        local key = RanchControl.key(zone)
        local existing = ranches[key]
        ranches[key] = existing or {
            zone = zone,
            originalName = zone:getName(),
            wasVanilla = zoneType == RanchControl.VANILLA_TYPE,
        }

        if zoneType == RanchControl.VANILLA_TYPE then
            zone:setType(RanchControl.CONTROLLED_TYPE)
        end
    end)

    return ranches
end

function RanchControl.restoreVanilla(metaGrid)
    local restored = 0
    local seen = {}

    visitRanchZones(metaGrid, function(zone, zoneType)
        if zoneType ~= RanchControl.CONTROLLED_TYPE then return end
        local key = RanchControl.key(zone)
        if seen[key] then return end
        seen[key] = true
        zone:setType(RanchControl.VANILLA_TYPE)
        restored = restored + 1
    end)

    return restored
end

return RanchControl
