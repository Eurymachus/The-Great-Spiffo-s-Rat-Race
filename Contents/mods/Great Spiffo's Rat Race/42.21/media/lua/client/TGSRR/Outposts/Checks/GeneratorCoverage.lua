local GeneratorCoverage = {}

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

function GeneratorCoverage.covers(outpost, generator)
    local zone = outpost and outpost.coreZone or nil
    local square = generator and generator.getSquare
        and generator:getSquare() or nil
    if not zone or not square or not IsoGenerator
            or not IsoGenerator.isPoweringSquare then
        return false
    end

    local generatorX = square:getX()
    local generatorY = square:getY()
    local targetX = clamp(generatorX, zone.minX, zone.maxX)
    local targetY = clamp(generatorY, zone.minY, zone.maxY)
    return IsoGenerator.isPoweringSquare(
        generatorX,
        generatorY,
        square:getZ(),
        targetX,
        targetY,
        outpost.sealingLevel or 0
    ) == true
end

return GeneratorCoverage
