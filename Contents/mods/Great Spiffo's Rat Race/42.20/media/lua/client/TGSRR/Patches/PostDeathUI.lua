require "ISUI/ISPostDeathUI"
require "ISUI/ISButton"

local Identity = require "TGSRR/Run/Identity"
local ExportMenu = require "TGSRR/Run/ExportMenu"
local TerminalState = require "TGSRR/Run/TerminalState"

local function TGSRR_isRatRaceChallenge()
    return Identity.isRatRaceChallenge()
end

if ISPostDeathUI and not ISPostDeathUI.TGSRR_postDeathPatched then
    local postDeathUICreateChildren = ISPostDeathUI.createChildren

    function ISPostDeathUI:createChildren()
        postDeathUICreateChildren(self)

        if TGSRR_isRatRaceChallenge() and self.buttonRespawn then
            local exportTitle = getText("UI_TGSRR_PostDeath_ExportFinalReport")
            local title = getText("UI_TGSRR_PostDeath_RespawnDisabled")
            local buttonHeight = self.buttonRespawn:getHeight()
            local buttonGap = self.buttonExit:getY()
                - self.buttonRespawn:getBottom()
            local rowHeight = buttonHeight + buttonGap

            self:setHeight(self:getHeight() + rowHeight)
            self:setY(self.screenY
                + (self.screenHeight - 40 - self:getHeight()))

            self.buttonRespawn:setY(self.buttonRespawn:getY() + rowHeight)
            self.buttonExit:setY(self.buttonExit:getY() + rowHeight)
            self.buttonQuit:setY(self.buttonQuit:getY() + rowHeight)

            self.tgsrrExportFinalReport = ISButton:new(
                self.buttonRespawn:getX(),
                0,
                self.buttonRespawn:getWidth(),
                buttonHeight,
                exportTitle,
                self,
                function()
                    local player = getSpecificPlayer(self.playerIndex or 0)
                    local finalized, finalizeError =
                        TerminalState.markDeceased(player)
                    if not finalized then
                        print("[TGSRR Run] Final report export blocked: "
                            .. tostring(finalizeError))
                        return
                    end
                    ExportMenu.exportRun()
                end
            )
            self:configButton(self.tgsrrExportFinalReport)
            self.tgsrrExportFinalReport:initialise()
            self.tgsrrExportFinalReport:instantiate()
            self:addChild(self.tgsrrExportFinalReport)

            self.buttonRespawn:setTitle(title)
            self.buttonRespawn:setEnable(false)
            self.buttonRespawn:enableDisabledColor()

            local width = math.max(
                getTextManager():MeasureStringX(UIFont.Small, title),
                getTextManager():MeasureStringX(UIFont.Small, exportTitle)
            ) + 20
            if width > self:getWidth() then
                self:setWidth(width)
                self:setX(self.screenX
                    + (self.screenWidth - width) / 2)
                self.tgsrrExportFinalReport:setWidth(width)
                self.buttonRespawn:setWidth(width)
                self.buttonExit:setWidth(width)
                self.buttonQuit:setWidth(width)
            end
        end
    end

    local postDeathUIPrerender = ISPostDeathUI.prerender

    function ISPostDeathUI:prerender()
        postDeathUIPrerender(self)
        if self.tgsrrExportFinalReport then
            self.tgsrrExportFinalReport:setVisible(self.waitOver)
        end
    end

    ISPostDeathUI.TGSRR_postDeathPatched = true
end
