require "ISUI/ISModalDialog"

local L = require "TGSRR/Core/Localization"

local TrackingHealth = {}

local activeModal = nil
local pending = {}
local reported = {}

local function message(alert)
    local title = L.text(
        "UI_TGSRR_TrackingStopped_Title",
        "Rat Race tracking has stopped"
    )
    local body = L.text(
        "UI_TGSRR_TrackingStopped_Body",
        "This session is no longer being recorded by the Rat Race tracker."
    )
    local reasonLabel = L.text(
        "UI_TGSRR_TrackingStopped_Reason",
        "Reason:"
    )
    local advice = L.text(
        "UI_TGSRR_TrackingStopped_Advice",
        "Save and quit if possible, then report this message.\n"
            .. "Progress made while tracking is stopped may not be recorded."
    )
    local detail = alert.detail ~= "" and ("\n" .. alert.detail) or ""
    return title .. "\n\n" .. body .. "\n\n"
        .. reasonLabel .. " " .. alert.reason .. detail .. "\n\n" .. advice
end

local function closed()
    activeModal = nil
end

local function showNext()
    if activeModal or #pending == 0 or not getCore() then return end
    local alert = table.remove(pending, 1)
    local width, height = 620, 250
    local modal = ISModalDialog:new(
        math.floor((getCore():getScreenWidth() - width) / 2),
        math.floor((getCore():getScreenHeight() - height) / 2),
        width,
        height,
        message(alert),
        false,
        nil,
        closed,
        0
    )
    modal:initialise()
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    activeModal = modal
end

function TrackingHealth.stop(reason, detail)
    reason = tostring(reason or "unknown_tracking_failure")
    detail = tostring(detail or "")
    local key = reason .. "\n" .. detail
    if reported[key] then return false end
    reported[key] = true
    pending[#pending + 1] = { reason = reason, detail = detail }
    print("[TGSRR Run] USER ALERT: tracking stopped: " .. reason
        .. (detail ~= "" and (" (" .. detail .. ")") or ""))
    showNext()
    return true
end

function TrackingHealth.onTick()
    showNext()
end

Events.OnTick.Add(TrackingHealth.onTick)

return TrackingHealth
