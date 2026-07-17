local Outposts = require "TGSRR/OutpostDefinitions"
local Envelope = require "TGSRR/OutpostExteriorEnvelope"

local function unavailable()
    return { available = false, passed = false, current = 0, required = 0 }
end

local function enclosureCheck(outpost, context)
    local envelope = Envelope.inspect(outpost, context)
    if not envelope.available then return unavailable() end

    local sealed = 0
    for _, segment in ipairs(envelope.segments) do
        if segment.sealed then sealed = sealed + 1 end
    end
    return {
        available = true,
        passed = #envelope.segments > 0 and sealed == #envelope.segments,
        current = sealed,
        required = #envelope.segments,
    }
end

local function doorCounts(outpost, context)
    local envelope = Envelope.inspect(outpost, context)
    if not envelope.available then return nil end

    local expected = 0
    local present = 0
    local closed = 0
    for _, segment in ipairs(envelope.segments) do
        if segment.doorFrame then
            expected = expected + 1
            if segment.door then
                present = present + 1
                if segment.doorClosed then closed = closed + 1 end
            end
        end
    end
    return expected, present, closed
end

local function doorsFittedCheck(outpost, context)
    local expected, present = doorCounts(outpost, context)
    if not expected then return unavailable() end
    return {
        available = true,
        passed = expected > 0 and present == expected,
        current = present,
        required = expected,
    }
end

local function doorsClosedCheck(outpost, context)
    local expected, present, closed = doorCounts(outpost, context)
    if not expected then return unavailable() end
    return {
        available = true,
        passed = expected > 0 and present == expected and closed == expected,
        current = closed,
        required = expected,
        present = present,
    }
end

Outposts.addCheck("enclosed", enclosureCheck, 30)
Outposts.addCheck("doors_fitted", doorsFittedCheck, 40)
Outposts.addCheck("doors_closed", doorsClosedCheck, 50)

return {
    enclosure = enclosureCheck,
    doorsFitted = doorsFittedCheck,
    doorsClosed = doorsClosedCheck,
}
