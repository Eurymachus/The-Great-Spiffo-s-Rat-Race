local Outposts = require "TGSRR/OutpostDefinitions"
local Envelope = require "TGSRR/OutpostExteriorEnvelope"

local function barricadeMaterial(barricade)
    if not barricade or barricade:isDestroyed() then return nil end
    if barricade:isMetal() then return "metal" end
    if barricade:isMetalBar() then return "metal_bar" end
    if barricade:getNumPlanks() > 0 then return "wood" end
    return nil
end

local function inspectBarricades(object)
    local sameMaterial = barricadeMaterial(object:getBarricadeOnSameSquare())
    local oppositeMaterial = barricadeMaterial(object:getBarricadeOnOppositeSquare())
    return sameMaterial ~= nil or oppositeMaterial ~= nil, sameMaterial, oppositeMaterial
end

local function inspectOpening(segment)
    local barricaded, sameMaterial, oppositeMaterial = inspectBarricades(segment.window)
    return {
        key = segment.key,
        x = segment.x,
        y = segment.y,
        z = segment.z,
        north = segment.north,
        kind = segment.windowKind,
        barricaded = barricaded,
        sameMaterial = sameMaterial,
        oppositeMaterial = oppositeMaterial,
    }
end

local function unavailable(scanned, missing)
    return {
        available = false,
        passed = false,
        current = 0,
        required = 0,
        scannedSquares = scanned or 0,
        missingSquares = missing or 0,
        openings = {},
    }
end

local function groundFloorWindowCheck(outpost, context)
    if not context or context.includeWindowSurvey ~= true then
        local result = unavailable(0, 0)
        result.deferred = true
        return result
    end

    local envelope = Envelope.inspect(outpost, context)
    if not envelope.available then
        return unavailable(#envelope.segments, envelope.missingSquares)
    end

    local openings = {}
    local barricaded = 0
    local scannedSquares = 0
    for _, segment in ipairs(envelope.segments) do
        scannedSquares = scannedSquares + 1
        if segment.window then
            local opening = inspectOpening(segment)
            openings[#openings + 1] = opening
            if opening.barricaded then barricaded = barricaded + 1 end
        end
    end

    return {
        available = true,
        passed = #openings > 0 and barricaded == #openings,
        current = barricaded,
        required = #openings,
        scannedSquares = scannedSquares,
        missingSquares = 0,
        envelopeSegments = #envelope.segments,
        openings = openings,
    }
end

Outposts.addCheck("ground_floor_windows", groundFloorWindowCheck, 20)

return groundFloorWindowCheck
