require "OptionScreens/LoadGameScreen"
require "OptionScreens/MainScreen"

local RAT_RACE_GAME_MODES = {
    ["The Great Spiffo's Rat Race"] = true,
    ["The Great Spiffo's Rat Race - CDDA"] = true,
    ["The Great Spiffo's Rat Race - Sprinters"] = true,
}

local function isRatRaceSave(info)
    return info and RAT_RACE_GAME_MODES[info.gameMode] == true
end

local function isDeadRatRaceSave(info)
    return isRatRaceSave(info) and info.playerAlive == false
end

local function isDeadRatRaceGameMode(info, gameMode)
    return isRatRaceSave(info)
        and info.gameMode == gameMode
        and info.playerAlive == false
end

local function getSaveInfoForGameMode(gameMode, saveName)
    return getSaveInfo(gameMode .. getFileSeparator() .. saveName)
end

if SaveInfoPanel and not SaveInfoPanel.TGSRR_deadSavePatched then
    local setRichText = SaveInfoPanel.setRichText

    function SaveInfoPanel:setRichText()
        local selected = self.parent.listbox.items[
            self.parent.listbox.selected
        ]
        if selected == self.richTextItem
                and selected == self.tgsrrDeadSaveRichTextItem then
            return
        end

        -- The load screen may have rendered the current selection before
        -- mod patches are installed. Invalidate vanilla's cache once so the
        -- existing selection is rebuilt with the Rat Race terminal message.
        if selected == self.richTextItem then
            self.richTextItem = nil
        end

        setRichText(self)

        if selected and isDeadRatRaceSave(selected.item) then
            self.richText.text = " <CENTER> <H1> <RED> "
                .. getText("UI_TGSRR_DeadSave_ContinuingDisabled")
                .. " <LINE> <LEFT> <TEXT> "
                .. self.richText.text
            self.richText:paginate()
        end
        self.tgsrrDeadSaveRichTextItem = selected
    end

    SaveInfoPanel.TGSRR_deadSavePatched = true
end

if ConfigPanel and not ConfigPanel.TGSRR_deadSavePatched then
    local setSavefile = ConfigPanel.setSavefile

    function ConfigPanel:setSavefile(folder, info)
        setSavefile(self, folder, info)
        if isRatRaceSave(info) then
            self.buttonNewPlayer:setEnable(false)
            self.buttonNewPlayer:enableDisabledColor()
            self.buttonNewPlayer:setTooltip(
                getText("UI_TGSRR_DeadSave_NewPlayerDisabled")
            )
        end
    end

    ConfigPanel.TGSRR_deadSavePatched = true
end

if LoadGameScreen and not LoadGameScreen.TGSRR_deadSavePatched then
    local disableBtn = LoadGameScreen.disableBtn

    function LoadGameScreen:disableBtn()
        disableBtn(self)
        local selected = self.listbox.items[self.listbox.selected]
        if selected and isDeadRatRaceSave(selected.item) then
            self.playButton:setEnable(false)
        end
    end

    LoadGameScreen.TGSRR_deadSavePatched = true
end

if MainScreen and not MainScreen.TGSRR_deadSavePatched then
    local function applyDeadSavePolicy(screen)
        if not screen or not MainScreen.latestSaveWorld then return end
        local info = getSaveInfoForGameMode(
            MainScreen.latestSaveGameMode,
            MainScreen.latestSaveWorld
        )
        if not isDeadRatRaceGameMode(
                info,
                MainScreen.latestSaveGameMode
        ) then
            return
        end

        screen.continueDisabled = true
        if screen.latestSaveOption then
            screen.latestSaveOption:setVisible(false)
        end
    end

    local startNormalMainScreen = MainScreen.startNormalMainScreen

    function MainScreen:startNormalMainScreen()
        applyDeadSavePolicy(self)
        startNormalMainScreen(self)
    end

    local continueLatestSave = MainScreen.continueLatestSave

    MainScreen.continueLatestSave = function(gameMode, saveName)
        if RAT_RACE_GAME_MODES[gameMode] and saveName then
            local info = getSaveInfoForGameMode(gameMode, saveName)
            if isDeadRatRaceGameMode(info, gameMode) then
                return
            end
        end
        return continueLatestSave(gameMode, saveName)
    end

    MainScreen.TGSRR_deadSavePatched = true
    applyDeadSavePolicy(MainScreen.instance)
end

if LoadGameScreen and LoadGameScreen.instance
        and LoadGameScreen.instance.infoPanel then
    LoadGameScreen.instance.infoPanel.richTextItem = nil
    LoadGameScreen.instance.infoPanel.tgsrrDeadSaveRichTextItem = nil
end
