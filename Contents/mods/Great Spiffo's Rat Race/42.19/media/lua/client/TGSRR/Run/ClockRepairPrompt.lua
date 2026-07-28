require "ISUI/ISModalDialog"

local L = require "TGSRR/Core/Localization"

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
    local modal = ISModalDialog:new(
        math.floor((getCore():getScreenWidth() - width) / 2),
        math.floor((getCore():getScreenHeight() - height) / 2),
        width,
        height,
        message(value),
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
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    activeModal = modal
    if setGameSpeed then setGameSpeed(0) end
    return true
end

return ClockRepairPrompt
