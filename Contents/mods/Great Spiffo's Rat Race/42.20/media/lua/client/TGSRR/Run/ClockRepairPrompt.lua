require "ISUI/ISModalDialog"

local L = require "TGSRR/Core/Localization"
local ModalLayout = require "TGSRR/Run/ModalLayout"

local ClockRepairPrompt = {}

local activeModal = nil

local function date(value)
    value = value or {}
    return string.format("%04d-%02d-%02d %05.2f",
        tonumber(value.calendar and value.calendar.year) or 0,
        tonumber(value.calendar and value.calendar.month) or 0,
        tonumber(value.calendar and value.calendar.day) or 0,
        tonumber(value.timeOfDay) or 0)
end

local function message(value)
    return table.concat({
        L.text("UI_TGSRR_ClockRepair_Title",
            "Game clock corruption detected"),
        "",
        L.text("UI_TGSRR_ClockRepair_Body",
            "The saved character survival clock matches an independent TGSRR checkpoint, but the world calendar or world-age clock does not."),
        L.text("UI_TGSRR_ClockRepair_Observed", "Observed:")
            .. " " .. date(value.observed)
            .. " / world age "
            .. string.format("%.3f", value.observed.worldAgeHours),
        L.text("UI_TGSRR_ClockRepair_Expected", "Expected:")
            .. " " .. date(value.expected)
            .. " / world age "
            .. string.format("%.3f", value.expected.worldAgeHours),
        "",
        L.text("UI_TGSRR_ClockRepair_Choice",
            "Repair restores the independently reconstructed clock and records moderator-visible recovery evidence."),
    }, "\n")
end

local function clicked(target, button)
    activeModal = nil
    if target and target.callback then
        target.callback(button.internal == "YES")
    end
end

function ClockRepairPrompt.show(value, callback)
    if activeModal then return false, "clock_repair_prompt_already_open" end
    local target = { callback = callback }
    local width, height = 760, 320
    local text = message(value)
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
        "UI_TGSRR_ClockRepair_Repair", "Repair Clock"))
    modal.no:setTitle(L.text(
        "UI_TGSRR_ClockRepair_Stop", "Do Not Continue"))
    local yesWidth = math.max(140,
        getTextManager():MeasureStringX(
            UIFont.Small, modal.yes:getTitle()) + 24)
    local noWidth = math.max(160,
        getTextManager():MeasureStringX(
            UIFont.Small, modal.no:getTitle()) + 24)
    modal.yes:setWidth(yesWidth)
    modal.no:setWidth(noWidth)
    modal.yes:setX(
        (modal:getWidth() - yesWidth - noWidth - 10) / 2)
    modal.no:setX(modal.yes:getRight() + 10)
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    activeModal = modal
    if setGameSpeed then setGameSpeed(0) end
    return true
end

return ClockRepairPrompt
