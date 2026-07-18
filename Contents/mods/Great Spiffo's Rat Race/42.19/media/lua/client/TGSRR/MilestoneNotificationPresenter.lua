local ChallengeEvents = require "TGSRR/ChallengeEvents"
local L = require "TGSRR/Localization"

local Presenter = {}

local function commaValue(value)
    local text = tostring(math.max(0, math.floor(tonumber(value) or 0)))
    while true do
        local replaced
        text, replaced = text:gsub("^(-?%d+)(%d%d%d)", "%1,%2")
        if replaced == 0 then return text end
    end
end

local function notificationText(payload)
    local definition = payload.definition or {}
    local text = L.text(definition.notificationKey, definition.notificationFallback or "Milestone reached")
    local source = payload.source or {}
    if source.threshold then text = text .. ": " .. commaValue(source.threshold) end
    return text
end

ChallengeEvents.subscribe("milestone.awarded", "milestone_notification_presenter", function(payload)
    local player = getSpecificPlayer(0) or getPlayer()
    if player and HaloTextHelper then HaloTextHelper.addGoodText(player, notificationText(payload)) end
end)

return Presenter
