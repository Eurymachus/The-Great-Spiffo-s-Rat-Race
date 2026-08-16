require "ISUI/ISButton"
require "ISUI/ISCollapsableWindow"

local LauncherPalette = require "TGSRR/Debug/LauncherPalette"
local ExportMenu = require "TGSRR/Run/ExportMenu"

local WINDOW_WIDTH = 250
local PADDING = 12
local BUTTON_HEIGHT = 32
local BUTTON_GAP = 8
local TESTS = {
    { label = "1 Year", days = 365 },
    { label = "2 Years", days = 730 },
    { label = "5 Years", days = 1825 },
    { label = "10 Years", days = 3650 },
}

TGSRR_ExportBenchmark = TGSRR_ExportBenchmark or {}
local State = TGSRR_ExportBenchmark
if State.window then
    State.window:removeFromUIManager()
    State.window = nil
end

local Window = ISCollapsableWindow:derive("TGSRRExportBenchmarkWindow")

function Window:createChildren()
    ISCollapsableWindow.createChildren(self)
    local y = self:titleBarHeight() + PADDING
    for _, test in ipairs(TESTS) do
        local button = ISButton:new(
            PADDING,
            y,
            self.width - PADDING * 2,
            BUTTON_HEIGHT,
            test.label,
            self,
            function(_, clickedButton)
                ExportMenu.exportSyntheticDays(clickedButton.tgsrrDays)
            end
        )
        button.tgsrrDays = test.days
        button:initialise()
        button:instantiate()
        self:addChild(button)
        y = y + BUTTON_HEIGHT + BUTTON_GAP
    end
end

function Window:close()
    self:setVisible(false)
    self:removeFromUIManager()
    if State.window == self then State.window = nil end
end

function Window:new()
    local height = 28 + PADDING * 2
        + #TESTS * BUTTON_HEIGHT
        + (#TESTS - 1) * BUTTON_GAP
    local x = math.floor((getCore():getScreenWidth() - WINDOW_WIDTH) / 2)
    local y = math.floor((getCore():getScreenHeight() - height) / 2)
    local window = ISCollapsableWindow.new(
        self, x, y, WINDOW_WIDTH, height)
    window.title = "TGSRR Export Tests"
    window.resizable = false
    window.pin = true
    window.alwaysOnTop = true
    return window
end

local function toggleWindow()
    if State.window then
        State.window:close()
        return
    end
    local window = Window:new()
    window:initialise()
    window:addToUIManager()
    window:setAlwaysOnTop(true)
    State.window = window
end

LauncherPalette.register(
    "export-benchmark",
    "TGSRR Exports",
    toggleWindow,
    35
)

return true
