local Envelope = require "TGSRR/Outposts/Checks/ExteriorEnvelope"
local Fixtures = require "TGSRR/Outposts/Checks/Fixtures"

local Guidance = {}
local activeOutpost = nil
local highlightedObjects = {}
local lastRefreshMs = 0
local REFRESH_INTERVAL_MS = 1000
local SINK_COLOR = ColorInfo.new(1.0, 0.65, 0.12, 1.0)
local WALL_COLOR = ColorInfo.new(1.0, 0.2, 0.08, 1.0)
local GENERATOR_COLOR = ColorInfo.new(1.0, 0.65, 0.12, 1.0)

local function playerNumber()
    local player = getSpecificPlayer(0) or getPlayer()
    return player and player:getPlayerNum() or 0
end

local function clearHighlights()
    local playerNum = playerNumber()
    for _, entry in ipairs(highlightedObjects) do
        local object = entry.object
        if object and object:getSquare() then object:setHighlighted(playerNum, false, false) end
    end
    highlightedObjects = {}
end

local function addHighlight(object, color)
    if object and object:getSquare() then
        highlightedObjects[#highlightedObjects + 1] = { object = object, color = color }
    end
end

local function collectSinkHighlights()
    local result = Fixtures.inspectPlumbedSink(activeOutpost)
    if not result or result.available ~= true or result.passed == true then return end
    local sinks = Fixtures.getSinksForOutpost(activeOutpost)
    if not sinks then return end

    for _, sink in ipairs(sinks) do
        addHighlight(sink, SINK_COLOR)
    end
end

local function collectWallHighlights()
    local inspection = Envelope.inspect(activeOutpost)
    if not inspection.available then return end
    local seen = {}
    for _, segment in ipairs(inspection.segments) do
        if not segment.sealed then
            local square = getCell():getGridSquare(segment.x, segment.y, segment.z)
            local floor = square and square:getFloor() or nil
            if floor and not seen[floor] then
                seen[floor] = true
                addHighlight(floor, WALL_COLOR)
            end
        end
    end
end

local function collectGeneratorHighlights()
    local result = Fixtures.inspectGenerator(activeOutpost)
    if not result or result.available ~= true or result.passed == true then return end
    for _, generator in ipairs(Fixtures.getGeneratorsForOutpost(activeOutpost)) do
        addHighlight(generator, GENERATOR_COLOR)
    end
end

local function refresh()
    lastRefreshMs = getTimestampMs()
    clearHighlights()
    if not activeOutpost then return end
    collectWallHighlights()
    collectSinkHighlights()
    collectGeneratorHighlights()
end

local function renderHighlights()
    local playerNum = playerNumber()
    for _, entry in ipairs(highlightedObjects) do
        local object = entry.object
        if object and object:getSquare() then
            object:setHighlighted(playerNum, true, false)
            object:setHighlightColor(playerNum, entry.color)
        end
    end
end

local function onRenderTick()
    if not activeOutpost then return end
    local now = getTimestampMs()
    if now - lastRefreshMs >= REFRESH_INTERVAL_MS then refresh() end
    renderHighlights()
end

function Guidance.isEnabled(outpost)
    return activeOutpost ~= nil and (not outpost or activeOutpost.id == outpost.id)
end

function Guidance.setEnabled(outpost, enabled)
    clearHighlights()
    activeOutpost = enabled == true and outpost or nil
    if activeOutpost then refresh() end
    return activeOutpost ~= nil
end

function Guidance.toggle(outpost)
    return Guidance.setEnabled(outpost, not Guidance.isEnabled(outpost))
end

Events.OnRenderTick.Add(onRenderTick)
Events.OnGameStart.Add(function() Guidance.setEnabled(nil, false) end)

return Guidance
