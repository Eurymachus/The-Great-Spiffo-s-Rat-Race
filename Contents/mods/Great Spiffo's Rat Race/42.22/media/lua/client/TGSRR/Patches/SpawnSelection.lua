require("OptionScreens/NewGameScreen")

if NewGameScreen.TGSRR_spawnSelectionPatched then return end

local challengeIds = { TGSRR = true, TGSRR_CDDA = true, TGSRR_Sprinters = true }
local clickPlay = NewGameScreen.clickPlay

function NewGameScreen:clickPlay()
    local data = self.selectedItem.data
    local challenge = data.challenge
    local result = clickPlay(self)

    -- 42.22.2 initializes challenges with a default spawn and skips this screen.
    -- Retain vanilla initialization, then offer the Rat Race spawn choices.
    if not data.arrowButton and challenge and challengeIds[challenge.id]
            and MapSpawnSelect.instance:hasChoices() then
        local spawnScreen = MapSpawnSelect.instance
        MainScreen.instance.charCreationProfession:setVisible(false)
        spawnScreen:fillList()
        spawnScreen.previousScreen = "NewGameScreen"
        spawnScreen:setVisible(true, self.joyfocus)
    end

    return result
end

NewGameScreen.TGSRR_spawnSelectionPatched = true
