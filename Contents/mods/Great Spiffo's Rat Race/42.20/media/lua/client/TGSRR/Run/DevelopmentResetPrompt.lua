require "ISUI/ISModalDialog"

local L = require "TGSRR/Core/Localization"
local ModalLayout = require "TGSRR/Run/ModalLayout"

local DevelopmentResetPrompt = {}

function DevelopmentResetPrompt.show(reset, newRunId)
    if not getCore() then return false end
    local message = table.concat({
        L.text(
            "UI_TGSRR_DevelopmentReset_Title",
            "Rat Race development data reset"
        ),
        "",
        L.text(
            "UI_TGSRR_DevelopmentReset_Body",
            "This save used an incompatible development data contract. Its TGSRR run state was reset and tracking restarted as a bootstrapped partial run."
        ),
        "",
        L.text("UI_TGSRR_DevelopmentReset_OldRun", "Previous run:")
            .. " " .. tostring(reset.oldRunId),
        L.text("UI_TGSRR_DevelopmentReset_NewRun", "Replacement run:")
            .. " " .. tostring(newRunId),
        L.text("UI_TGSRR_DevelopmentReset_Reason", "Reason:")
            .. " " .. tostring(reset.reason),
        "",
        L.text(
            "UI_TGSRR_DevelopmentReset_Preserved",
            "The previous external run files were preserved and are no longer used by this save."
        ),
    }, "\n")
    local width, height = 720, 300
    local x, y
    x, y, width, height =
        ModalLayout.fitAndCenter(width, height, message, 0)
    local modal = ISModalDialog:new(
        x,
        y,
        width,
        height,
        message,
        false,
        nil,
        function() end,
        0
    )
    modal:initialise()
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    return true
end

return DevelopmentResetPrompt
