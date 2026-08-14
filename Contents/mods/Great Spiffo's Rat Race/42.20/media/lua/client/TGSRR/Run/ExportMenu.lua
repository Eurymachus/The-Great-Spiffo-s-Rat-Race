require "OptionScreens/MainScreen"
require "ISUI/ISLabel"
require "ISUI/ISModalDialog"
require "ISUI/ISPanel"
require "ISUI/ISButton"

local Identity = require "TGSRR/Run/Identity"
local Exporter = require "TGSRR/Run/Exporter"
local L = require "TGSRR/Core/Localization"
local ModalLayout = require "TGSRR/Run/ModalLayout"

local ExportMenu = {}
local ExportOverlay = ISPanel:derive("TGSRRExportOverlay")
local activeExport = nil
local updateExport

function ExportOverlay:prerender()
    self:drawRect(0, 0, self.width, self.height, 0.9, 0, 0, 0)
    self:drawRectBorder(0, 0, self.width, self.height, 1, 0.4, 0.4, 0.4)
    local dotCount = math.floor(getTimestampMs() / 400) % 3 + 1
    local label = L.text("UI_TGSRR_Tracker_Exporting", "Exporting data")
    local textManager = getTextManager()
    local labelWidth = textManager:MeasureStringX(UIFont.Medium, label)
    local dotsWidth = textManager:MeasureStringX(UIFont.Medium, "...")
    local labelX = math.floor((self.width - labelWidth - dotsWidth) / 2)
    self:drawText(label, labelX, 24, 1, 1, 1, 1, UIFont.Medium)
    local dotX = labelX + labelWidth
    local singleDotWidth = textManager:MeasureStringX(UIFont.Medium, ".")
    for index = 1, 3 do
        self:drawText(".", dotX + (index - 1) * singleDotWidth, 24,
            1, 1, 1, index <= dotCount and 1 or 0, UIFont.Medium)
    end
    local phase = activeExport and activeExport.job and activeExport.job.phase or "prepare"
    self:drawTextCentre(
        L.text("UI_TGSRR_Tracker_ExportPhase_" .. tostring(phase), tostring(phase)),
        self.width / 2,
        58,
        0.7, 0.7, 0.7, 1,
        UIFont.Small
    )
end

function ExportOverlay:onMouseDown()
    self.moving = true
    self:bringToTop()
    return true
end

function ExportOverlay:onMouseMove(dx, dy)
    if self.moving then
        self:setX(self:getX() + dx)
        self:setY(self:getY() + dy)
    end
end

function ExportOverlay:onMouseMoveOutside(dx, dy)
    self:onMouseMove(dx, dy)
end

function ExportOverlay:onMouseUp()
    self.moving = false
end

function ExportOverlay:onMouseUpOutside()
    self.moving = false
end

function ExportOverlay:new()
    local width, height = 440, 110
    local x, y = ModalLayout.center(width, height, 0)
    local o = ISPanel.new(
        self,
        x,
        y,
        width,
        height
    )
    o.moving = false
    return o
end

local function showMessage(message, buttonText, onclick, param1)
    local width, height = 440, 180
    local x, y
    x, y, width, height =
        ModalLayout.fitAndCenter(width, height, message, 0)
    local modal = ISModalDialog:new(
        x,
        y,
        width, height, message, false, nil, onclick, nil, param1
    )
    modal:initialise()
    if buttonText and modal.ok then
        modal.ok:setTitle(buttonText)
        local buttonWidth = math.max(
            100,
            getTextManager():MeasureStringX(UIFont.Small, buttonText) + 24
        )
        modal.ok:setWidth(buttonWidth)
        modal.ok:setX((modal:getWidth() - buttonWidth) / 2)
    end
    modal:setAlwaysOnTop(true)
    modal:addToUIManager()
    return modal
end

local function finishExport(ok, result)
    if activeExport and activeExport.overlay then
        activeExport.overlay:setVisible(false)
        activeExport.overlay:removeFromUIManager()
    end
    activeExport = nil

    if not ok then
        showMessage(L.text("UI_TGSRR_Tracker_ExportFailed", "Export failed:") ..
            "\n" .. tostring(result))
        return
    end

    local readyText = L.text("UI_TGSRR_Tracker_ExportReady", "Run export ready.")
    local summaryText = tostring(result.eventSequence) .. " " ..
        L.text("UI_TGSRR_Tracker_ExportEvents", "events") .. "  |  " ..
        tostring(result.encodedCharacters) .. " " ..
        L.text("UI_TGSRR_Tracker_ExportCharacters", "characters")
    local modal = showMessage(
        readyText .. "\n\n" .. summaryText,
        L.text("UI_TGSRR_Tracker_CopyToClipboard", "Copy to Clipboard")
    )
    modal.exportCopied = false
    modal.prerender = function(self)
        self:drawRect(0, 0, self.width, self.height,
            self.backgroundColor.a, self.backgroundColor.r,
            self.backgroundColor.g, self.backgroundColor.b)
        self:drawRectBorder(0, 0, self.width, self.height,
            self.borderColor.a, self.borderColor.r,
            self.borderColor.g, self.borderColor.b)
        self:drawTextCentre(readyText, self:getWidth() / 2, 24,
            1, 1, 1, 1, UIFont.Small)
        self:drawTextCentre(summaryText, self:getWidth() / 2, 68,
            1, 1, 1, 1, UIFont.Small)
        if self.exportCopied then
            self:drawTextCentre(
                L.text("UI_TGSRR_Tracker_CopiedToClipboard", "Copied to Clipboard"),
                self:getWidth() / 2,
                108,
                1, 1, 1, 1,
                UIFont.Small
            )
        end
    end
    local closeText = L.text("UI_TGSRR_Tracker_Close", "Close")
    local closeWidth = math.max(
        100,
        getTextManager():MeasureStringX(UIFont.Small, closeText) + 24
    )
    local buttonGap = 10
    local buttonGroupWidth = modal.ok:getWidth() + buttonGap + closeWidth
    modal.ok:setX((modal:getWidth() - buttonGroupWidth) / 2)
    local closeButton = ISButton:new(
        modal.ok:getRight() + buttonGap,
        modal.ok:getY(),
        closeWidth,
        modal.ok:getHeight(),
        closeText,
        modal,
        function(target)
            target:destroy()
        end
    )
    closeButton:initialise()
    closeButton:instantiate()
    closeButton:enableCancelColor()
    modal:addChild(closeButton)
    modal.ok.onclick = function()
        Clipboard.setClipboard(result.value)
        modal.exportCopied = true
    end
end

updateExport = function()
    if not activeExport then return end
    local ok, result = Exporter.step(activeExport.job)
    if activeExport.job.done then finishExport(ok, result) end
end

function ExportMenu.exportRun()
    if activeExport then return end

    -- Leave the Escape menu before creating the export UI. ToggleEscapeMenu
    -- resumes the game, so restore the pause while this modal task runs.
    if MainScreen.instance and MainScreen.instance.inGame and MainScreen.instance:isVisible() then
        ToggleEscapeMenu(getCore():getKey("Main Menu"))
    end
    local speedControls = UIManager.getSpeedControls()
    if speedControls then
        speedControls:SetCurrentGameSpeed(0)
    else
        setGameSpeed(0)
    end
    setShowPausedMessage(true)

    local overlay = ExportOverlay:new()
    overlay:initialise()
    overlay:setAlwaysOnTop(true)
    overlay:addToUIManager()
    activeExport = {
        overlay = overlay,
        job = Exporter.begin(),
    }
end

local originalMenuItemMouseDown = MainScreen.onMenuItemMouseDownMainMenu
MainScreen.onMenuItemMouseDownMainMenu = function(item, x, y)
    if item and item.internal == "TGSRR_EXPORT" then
        getSoundManager():playUISound("UIActivateMainMenuItem")
        ExportMenu.exportRun()
        return
    end
    return originalMenuItemMouseDown(item, x, y)
end

local originalInstantiate = MainScreen.instantiate
function MainScreen:instantiate()
    originalInstantiate(self)
    if not self.inGame or not Identity.isRatRaceChallenge() or self.tgsrrExportOption then return end

    local labelHeight = self.exitOption and self.exitOption:getHeight()
        or getTextManager():getFontHeight(UIFont.Large) + 16
    local labelSeparator = 16
    local labelX = self.exitOption and self.exitOption:getX() or 0
    local labelY = self.exitOption and self.exitOption:getY() or self.bottomPanel:getHeight()

    for _, child in pairs(self.bottomPanel:getChildren()) do
        if child.Type == "ISLabel" and child:getY() >= labelY then
            child:setY(child:getY() + labelHeight + labelSeparator)
        end
    end

    self.tgsrrExportOption = ISLabel:new(
        labelX, labelY, labelHeight,
        L.text("UI_TGSRR_Tracker_Export", "EXPORT"),
        1, 1, 1, 1, UIFont.Large, true
    )
    self.tgsrrExportOption.internal = "TGSRR_EXPORT"
    self.tgsrrExportOption:initialise()
    self.tgsrrExportOption.onMouseDown = MainScreen.onMenuItemMouseDownMainMenu
    self.bottomPanel:addChild(self.tgsrrExportOption)
    self.bottomPanel:setHeight(self.bottomPanel:getHeight() + labelHeight + labelSeparator)

    -- MainScreen applies this native button treatment before modded entries
    -- are appended. Normalize every injected label so they align, highlight,
    -- and size exactly like the vanilla menu rows.
    local width = self.bottomPanel:getWidth()
    for _, child in pairs(self.bottomPanel:getChildren()) do
        if child.Type == "ISLabel" then width = math.max(width, child:getWidth()) end
    end
    local widthDelta = width - self.bottomPanel:getWidth()
    if widthDelta > 0 then self.bottomPanel:setX(self.bottomPanel:getX() - widthDelta / 2) end
    self.bottomPanel:setWidth(width)
    for _, child in pairs(self.bottomPanel:getChildren()) do
        if child.Type == "ISLabel" then
            child:setWidth(width)
            if not child.fade then
                child.fade = UITransition.new()
                child.fade:setFadeIn(false)
                child.prerender = MainScreen.prerenderBottomPanelLabel
            end
        end
    end
    self.maxMenuItemWidth = width
end

local originalOnGainJoypadFocus = MainScreen.onGainJoypadFocus
function MainScreen:onGainJoypadFocus(joypadData)
    originalOnGainJoypadFocus(self, joypadData)
    local option = self.tgsrrExportOption
    if not option or not option:isVisible() then return end
    option:setJoypadFocused(false)
    local insertAt = #self.joypadButtonsY + 1
    for index, row in ipairs(self.joypadButtonsY) do
        if row[1]:getY() > option:getY() then
            insertAt = index
            break
        end
    end
    table.insert(self.joypadButtonsY, insertAt, { option })
end

Events.OnTickEvenPaused.Add(function()
    updateExport()
end)

return ExportMenu
