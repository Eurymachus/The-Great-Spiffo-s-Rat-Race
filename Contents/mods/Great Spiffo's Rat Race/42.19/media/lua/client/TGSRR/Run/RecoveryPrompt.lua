require "ISUI/ISModalDialog"

local L = require "TGSRR/Core/Localization"
local ModalLayout = require "TGSRR/Run/ModalLayout"

local RecoveryPrompt = {}

local activeModal = nil

local function eventSummary(recovery)
    local values = {}
    for _, eventType in ipairs(recovery.eventTypes or {}) do
        values[#values + 1] = tostring(eventType) .. " x "
            .. tostring(recovery.eventTypeCounts[eventType] or 0)
    end
    return #values > 0 and table.concat(values, ", ")
        or L.text("UI_TGSRR_Recovery_UnknownEvents", "Unknown events")
end

local function message(recovery)
    return table.concat({
        L.text("UI_TGSRR_Recovery_Title", "Save rollback detected"),
        "",
        L.text(
            "UI_TGSRR_Recovery_Body",
            "The external run ledger contains gameplay recorded after this save checkpoint."
        ),
        L.text("UI_TGSRR_Recovery_SaveCursor", "Save checkpoint:")
            .. " " .. tostring(recovery.checkpointSequence),
        L.text("UI_TGSRR_Recovery_LedgerCursor", "Ledger head:")
            .. " " .. tostring(recovery.supersededEventSequence),
        L.text("UI_TGSRR_Recovery_AheadEvents", "Ahead events:")
            .. " " .. eventSummary(recovery),
        "",
        L.text(
            "UI_TGSRR_Recovery_Choice",
            "Continue creates a declared recovery branch and preserves the later history for moderator review."
        ),
    }, "\n")
end

local function clicked(target, button)
    activeModal = nil
    if target and target.callback then
        target.callback(button.internal == "YES")
    end
end

function RecoveryPrompt.show(recovery, callback)
    if activeModal then return false, "recovery_prompt_already_open" end
    local target = { callback = callback }
    local width, height = 680, 300
    local text = message(recovery)
    local x, y
    x, y, width, height =
        ModalLayout.fitAndCenter(width, height, text, 0)
    local modal = ISModalDialog:new(
        x,
        y,
        width,
        height,
        text,
        true,
        target,
        clicked,
        0
    )
    modal:initialise()
    modal.yes:setTitle(L.text(
        "UI_TGSRR_Recovery_Continue", "Continue as Recovered Run"))
    modal.no:setTitle(L.text(
        "UI_TGSRR_Recovery_Quit", "Do Not Continue"))
    local yesWidth = math.max(180,
        getTextManager():MeasureStringX(UIFont.Small, modal.yes:getTitle()) + 24)
    local noWidth = math.max(140,
        getTextManager():MeasureStringX(UIFont.Small, modal.no:getTitle()) + 24)
    modal.yes:setWidth(yesWidth)
    modal.no:setWidth(noWidth)
    modal.yes:setX((modal:getWidth() - yesWidth - noWidth - 10) / 2)
    modal.no:setX(modal.yes:getRight() + 10)
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    activeModal = modal
    if setGameSpeed then setGameSpeed(0) end
    return true
end

return RecoveryPrompt
