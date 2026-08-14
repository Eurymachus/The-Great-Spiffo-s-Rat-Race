require "ISUI/ISCollapsableWindow"
require "ISUI/ISButton"

local Exporter = require "TGSRR/Debug/RSLBuildingIdExporter"
local Records = require "TGSRR/Debug/RSLBuildingIdData"
local LauncherPalette = require "TGSRR/Debug/LauncherPalette"

local Window = ISCollapsableWindow:derive("TGSRRRSLBuildingIdWindow")
Window.instance = nil

function Window:createChildren()
    ISCollapsableWindow.createChildren(self)
    local button = ISButton:new(12, 42, self.width - 24, 28, "Export Building IDs", self, Window.onExport)
    button:initialise()
    button:instantiate()
    self:addChild(button)
    self.exportButton = button
end

function Window:onExport()
    self.exportButton:setEnable(false)
    self.status = "Resolving " .. tostring(#Records) .. " locations..."

    local ok, result = Exporter.run(Records)
    if ok then
        self.status = string.format(
            "Done: %d resolved, %d unresolved, %d unique buildings.",
            result.resolved, result.unresolved, result.uniqueBuildings)
    else
        self.status = "Export failed: " .. tostring(result)
    end
    self.exportButton:setEnable(true)
    print("[TGSRR RSL Building IDs] " .. self.status)
end

function Window:render()
    ISCollapsableWindow.render(self)
    if self.isCollapsed then return end
    self:drawText(self.status, 12, 82, 1, 1, 1, 1, UIFont.Small)
    self:drawText("Records: " .. tostring(#Records), 12, 108, 0.75, 0.75, 0.75, 1, UIFont.Small)
    self:drawText("Output: " .. Exporter.getOutputFile(), 12, 128, 0.75, 0.75, 0.75, 1, UIFont.Small)
end

function Window:new(x, y)
    local o = ISCollapsableWindow.new(self, x, y, 460, 170)
    o.title = "TGSRR RSL Building ID Exporter"
    o.resizable = false
    o.pin = true
    o.status = "Ready. Use the active map set you want to inspect."
    return o
end

local function getOrCreateWindow()
    if Window.instance then return Window.instance end
    local width, height = 460, 170
    local x = math.floor((getCore():getScreenWidth() - width) / 2)
    local y = math.floor((getCore():getScreenHeight() - height) / 2)
    local window = Window:new(x, y)
    window:initialise()
    Window.instance = window
    return window
end

local function toggleWindow()
    local window = getOrCreateWindow()
    if window:getIsVisible() then
        window:setVisible(false)
    else
        window:addToUIManager()
        window:setVisible(true)
        window:bringToTop()
    end
end

LauncherPalette.register("rsl-building-ids", "RSL Building IDs", toggleWindow, 30)

return Window
