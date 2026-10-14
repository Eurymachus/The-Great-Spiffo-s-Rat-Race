local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.21/media/lua/"
package.path = sourceRoot .. "client/?.lua;" .. package.path

local now, started, paused = 0, 0, 0
local run = { lifecycle = "deceased" }
local tick
local function noop() end
for _, name in ipairs({ "OptionScreens/MainScreen", "ISUI/ISLabel",
        "ISUI/ISModalDialog", "ISUI/ISPanel", "ISUI/ISButton" }) do
    package.loaded[name] = true
end
MainScreen = {}
ISPanel = {
    derive = function() return {} end,
    new = function()
        return { initialise = noop, setAlwaysOnTop = noop, addToUIManager = noop }
    end,
}
UIManager = { getSpeedControls = function()
    return { SetCurrentGameSpeed = function() paused = paused + 1 end }
end }
setShowPausedMessage = noop
getTimestampMs = function() return now end
Events = { OnTickEvenPaused = { Add = function(callback) tick = callback end } }
package.loaded["TGSRR/Run/Identity"] = {
    get = function() return run end,
    isRatRaceChallenge = function() return true end,
}
package.loaded["TGSRR/Run/Exporter"] = {
    begin = function() started = started + 1; return {} end,
    step = noop,
}
package.loaded["TGSRR/Core/Localization"] = {}
package.loaded["TGSRR/Run/ModalLayout"] = { center = function() return 0, 0 end }

local function freshMenu()
    package.loaded["TGSRR/Run/ExportMenu"] = nil
    return require("TGSRR/Run/ExportMenu")
end

local menu = freshMenu()
menu.scheduleDeathExport()
now = 9999
tick()
assert(started == 0 and paused == 0, "death animation must remain unpaused")
menu.scheduleDeathExport()
now = 10000
tick()
assert(started == 1 and paused == 1, "duplicate scheduling must not postpone export")
tick()
assert(started == 1, "automatic export must open only once")

menu = freshMenu()
menu.scheduleDeathExport()
menu.exportRun()
now = 20000
tick()
assert(started == 2, "manual export must satisfy the pending automatic export")

menu = freshMenu()
menu.scheduleDeathExport()
run = { lifecycle = "active" }
now = 30000
tick()
assert(started == 2, "a pending export must not follow a replacement run")
print("death export delay test passed")
