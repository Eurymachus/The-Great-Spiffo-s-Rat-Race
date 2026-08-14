local ChallengeEvents = require "TGSRR/Core/Events"
local Ledger = require "TGSRR/Milestones/Ledger"

local Registry = {}
local definitions = {}
local ordered = {}
local subscribedEvents = {}

local function currentMode()
    local core = getCore and getCore() or nil
    return core and core:getGameMode() or nil
end

local function modeAllowed(definition)
    if type(definition.modes) ~= "table" then return true end
    local mode = currentMode()
    for _, allowed in ipairs(definition.modes) do
        if allowed == mode then return true end
    end
    return false
end

local function claimKey(definition, event)
    if type(definition.claimKey) == "function" then return definition.claimKey(event) end
    return definition.id
end

local function dispatch(eventName, event)
    for _, definition in ipairs(ordered) do
        if definition.event == eventName and modeAllowed(definition)
                and (not definition.enabled or definition.enabled(event) == true)
                and (not definition.matches or definition.matches(event) == true) then
            local key = claimKey(definition, event)
            if definition.repeatable == true or not Ledger.isClaimed(key) then
                local awarded = true
                if definition.award then
                    local ok, result = pcall(definition.award, event)
                    awarded = ok and result ~= false
                end
                if awarded and (definition.repeatable == true or Ledger.claim(key, {
                        milestoneId = definition.id,
                        event = eventName,
                    })) then
                    ChallengeEvents.emit("milestone.awarded", {
                        definition = definition,
                        source = event,
                        claimKey = key,
                    })
                end
            end
        end
    end
end

function Registry.register(definition)
    if not definition or not definition.id or not definition.event then return false end
    if definitions[definition.id] then return false end
    definitions[definition.id] = definition
    ordered[#ordered + 1] = definition
    table.sort(ordered, function(a, b)
        return (a.order or 0) < (b.order or 0)
    end)
    if not subscribedEvents[definition.event] then
        subscribedEvents[definition.event] = true
        ChallengeEvents.subscribe(definition.event, "milestone_registry:" .. definition.event,
            function(event) dispatch(definition.event, event) end)
    end
    return true
end

function Registry.get(id) return definitions[id] end
function Registry.getAll() return ordered end
function Registry.isClaimed(definition, event)
    return Ledger.isClaimed(claimKey(definition, event or {}))
end

return Registry
