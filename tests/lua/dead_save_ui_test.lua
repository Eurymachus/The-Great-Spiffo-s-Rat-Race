local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;" .. package.path

package.loaded["OptionScreens/LoadGameScreen"] = true
package.loaded["OptionScreens/MainScreen"] = true

SaveInfoPanel = nil
ConfigPanel = nil
LoadGameScreen = nil

local originalCalls = 0
local requestedPath = nil
local saveInfo = nil

function getFileSeparator()
    return "/"
end

function getSaveInfo(path)
    requestedPath = path
    return saveInfo
end

MainScreen = {
    continueLatestSave = function()
        originalCalls = originalCalls + 1
    end,
}

require "TGSRR/Patches/DeadSaveUI"

local gameMode = "The Great Spiffo's Rat Race"
local saveName = "Test Save"

saveInfo = {
    gameMode = gameMode,
    playerAlive = true,
}
MainScreen.continueLatestSave(gameMode, saveName)
assert(requestedPath == gameMode .. "/" .. saveName)
assert(originalCalls == 1)

saveInfo.playerAlive = false
MainScreen.continueLatestSave(gameMode, saveName)
assert(originalCalls == 1)

saveInfo = {
    gameMode = "Sandbox",
    playerAlive = false,
}
MainScreen.continueLatestSave(gameMode, saveName)
assert(originalCalls == 2)

print("dead save UI test passed")
