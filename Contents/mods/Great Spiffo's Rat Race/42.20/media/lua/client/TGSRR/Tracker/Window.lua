require "ISUI/ISCollapsableWindow"
require "ISUI/ISButton"

local Tracker = require "TGSRR/Challenge/TrackerRegistry"
local State = require "TGSRR/Tracker/State"
local L = require "TGSRR/Core/Localization"
local Identity = require "TGSRR/Run/Identity"
local Layout = require "TGSRR/Tracker/Layout"
local DangerAutoClose = require "TGSRR/Tracker/DangerAutoClose"
require "TGSRR/Tracker/Overview/Module"
require "TGSRR/Tracker/Kills/Module"
require "TGSRR/Notifications/MilestonePresenter"
require "TGSRR/Tracker/Skills/Module"
require "TGSRR/Tracker/Outposts/Module"
require "TGSRR/Tracker/Landmarks/Module"

TGSRRChallengeTrackerWindow = ISCollapsableWindow:derive("TGSRRChallengeTrackerWindow")
TGSRRChallengeTrackerWindow.instance = nil
TGSRRChallengeTrackerWindow.launcher = nil

local CONTENT_MARGIN = 6
local WINDOW_WIDTH = 800
local WINDOW_HEIGHT = 650
local LAUNCHER_SIZE = 58
local LAUNCHER_MARGIN = 4
local LAUNCHER_TEXTURE_OFF = "media/ui/TGSRR_TrackerLauncher48_off.png"
local LAUNCHER_TEXTURE_ON = "media/ui/TGSRR_TrackerLauncher48_on.png"
local DRAG_THRESHOLD = 4

local function windowWidth()
    local modules = Tracker.getModules()
    local widestTab = 0
    local widestView = 0
    for _, module in ipairs(modules) do
        widestTab = math.max(widestTab, Layout.tabWidth(module.title))
        if module.minimumWidth then
            widestView = math.max(widestView, module.minimumWidth())
        end
    end
    local tabContentWidth = widestTab * #modules
    local viewContentWidth = widestView + CONTENT_MARGIN * 2
    return math.min(getCore():getScreenWidth(),
        math.max(WINDOW_WIDTH, tabContentWidth, viewContentWidth))
end

local function tabHeight()
    return Layout.boxHeight(UIFont.Small, 7, 28)
end

local function tabWidths(modules, availableWidth)
    local widths = {}
    local count = #modules
    if count == 0 then return widths end

    local baseWidth = math.floor(availableWidth / count)
    local remainder = availableWidth - baseWidth * count
    for index = 1, count do
        widths[index] = baseWidth
        if index <= remainder then widths[index] = widths[index] + 1 end
    end
    return widths
end

local TGSRRTrackerLauncher = ISButton:derive("TGSRRTrackerLauncher")

function TGSRRTrackerLauncher:render()
    local window = TGSRRChallengeTrackerWindow.instance
    local active = self.mouseOver or (window and window:getIsVisible())
    self.image = active and self.imageOn or self.imageOff
    ISButton.render(self)
end

function TGSRRTrackerLauncher:onMouseDown(x, y)
    ISButton.onMouseDown(self, x, y)
    self.dragging = true
    self.wasDragged = false
    self.dragStartMouseX = getMouseX()
    self.dragStartMouseY = getMouseY()
    self.dragStartX = self:getX()
    self.dragStartY = self:getY()
end

function TGSRRTrackerLauncher:onMouseMove(dx, dy)
    ISButton.onMouseMove(self, dx, dy)
    if not self.dragging then return end

    local deltaX = getMouseX() - self.dragStartMouseX
    local deltaY = getMouseY() - self.dragStartMouseY
    if not self.wasDragged and
            (math.abs(deltaX) >= DRAG_THRESHOLD or math.abs(deltaY) >= DRAG_THRESHOLD) then
        self.wasDragged = true
    end
    if not self.wasDragged then return end

    local maxX = math.max(0, getCore():getScreenWidth() - self:getWidth())
    local maxY = math.max(0, getCore():getScreenHeight() - self:getHeight())
    self:setX(math.max(0, math.min(maxX, self.dragStartX + deltaX)))
    self:setY(math.max(0, math.min(maxY, self.dragStartY + deltaY)))
end

function TGSRRTrackerLauncher:onMouseMoveOutside(dx, dy)
    self:onMouseMove(dx, dy)
end

function TGSRRTrackerLauncher:finishDrag()
    local wasDragged = self.wasDragged
    self.dragging = false
    self.wasDragged = false
    if wasDragged then State.save(nil, self) end
    return wasDragged
end

function TGSRRTrackerLauncher:onMouseUp(x, y)
    if self:finishDrag() then
        self.pressed = false
        return
    end
    ISButton.onMouseUp(self, x, y)
end

function TGSRRTrackerLauncher:onMouseUpOutside(x, y)
    self:finishDrag()
    ISButton.onMouseUpOutside(self, x, y)
end

local function isRatRace()
    return Identity.isRatRaceChallenge()
end

function TGSRRChallengeTrackerWindow:createChildren()
    ISCollapsableWindow.createChildren(self)
    self.tabs = {}
    self.views = {}
    local tabY = self:titleBarHeight()
    local tabsHeight = tabHeight()
    self.tabPanel = ISPanel:new(0, tabY, self.width, tabsHeight)
    self.tabPanel:initialise()
    self.tabPanel.backgroundColor = { r = 0, g = 0, b = 0, a = 0.65 }
    self:addChild(self.tabPanel)

    local modules = Tracker.getModules()
    local widths = tabWidths(modules, self.width)
    local tabX = 0
    for index, module in ipairs(modules) do
        local button = ISButton:new(tabX, 0, widths[index], tabsHeight,
            module.title, self, self.onTab)
        button.moduleId = module.id
        button:initialise(); button:instantiate(); self.tabPanel:addChild(button)
        self.tabs[module.id] = button

        tabX = tabX + widths[index]
        local contentY = tabY + tabsHeight
        local contentHeight = self.height - contentY - CONTENT_MARGIN
        local view = module.createView(self, CONTENT_MARGIN, contentY,
            self.width - CONTENT_MARGIN * 2, contentHeight)
        view:initialise(); view:instantiate(); view:setVisible(false); self:addChild(view)
        self.views[module.id] = view
    end
    local selectedId = self.activeModuleId
    if not selectedId or not self.views[selectedId] then selectedId = modules[1] and modules[1].id end
    self:selectTab(selectedId)
end

function TGSRRChallengeTrackerWindow:onTab(button) self:selectTab(button.moduleId) end

function TGSRRChallengeTrackerWindow:selectTab(id)
    if not id or not self.views[id] then return end
    for moduleId, view in pairs(self.views) do
        if moduleId == id then
            if view.onShow then view:onShow() else view:setVisible(true) end
        else
            if view.onHide then view:onHide() else view:setVisible(false) end
        end
        self.tabs[moduleId].backgroundColor = moduleId == id and
            { r = 0.28, g = 0.28, b = 0.28, a = 0.95 } or
            { r = 0.05, g = 0.05, b = 0.05, a = 0.75 }
    end
    self.activeModuleId = id
end

function TGSRRChallengeTrackerWindow:onResize()
    ISCollapsableWindow.onResize(self)
    local tabY = self:titleBarHeight()
    local tabsHeight = tabHeight()
    local y = tabY + tabsHeight
    local width = self.width - CONTENT_MARGIN * 2
    local height = self.height - y - CONTENT_MARGIN
    if self.tabPanel then
        self.tabPanel:setY(tabY)
        self.tabPanel:setWidth(self.width)
    end
    local modules = Tracker.getModules()
    local widths = tabWidths(modules, self.width)
    local tabX = 0
    for index, module in ipairs(modules) do
        local tab = self.tabs and self.tabs[module.id]
        if tab then
            tab:setX(tabX); tab:setY(0); tab:setWidth(widths[index]); tab:setHeight(tabsHeight)
        end
        tabX = tabX + widths[index]
        local view = self.views and self.views[module.id]
        if view and view.onResize then view:onResize(width, height) end
    end
end

function TGSRRChallengeTrackerWindow:saveState() State.save(self, nil, self:getIsVisible()) end
function TGSRRChallengeTrackerWindow:update()
    ISCollapsableWindow.update(self)
    if self:getIsVisible() and DangerAutoClose.shouldClose(getSpecificPlayer(0) or getPlayer()) then
        self:close()
    end
end
function TGSRRChallengeTrackerWindow:onMouseUp(x, y) ISCollapsableWindow.onMouseUp(self, x, y); self:saveState() end
function TGSRRChallengeTrackerWindow:onMouseUpOutside(x, y) ISCollapsableWindow.onMouseUpOutside(self, x, y); self:saveState() end
function TGSRRChallengeTrackerWindow:close()
    State.save(self, nil, false)
    self:setVisible(false)
end

function TGSRRChallengeTrackerWindow:new(x, y, width, height)
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.title = L.text("UI_TGSRR_Tracker_Title", "The Great Spiffo's Rat Race")
    o.resizable = false
    o:setResizable(false)
    return o
end

function TGSRRChallengeTrackerWindow.open()
    local window = TGSRRChallengeTrackerWindow.instance
    if window then
        window:setVisible(true)
        window:addToUIManager()
        local view = window.views and window.views[window.activeModuleId]
        if view and view.onShow then view:onShow() end
        State.save(window, nil, true)
        return window
    end
    local saved = State.load()
    local width = windowWidth()
    local height = WINDOW_HEIGHT
    local maxX = math.max(0, getCore():getScreenWidth() - width)
    local maxY = math.max(0, getCore():getScreenHeight() - height)
    local x = math.max(0, math.min(maxX,
        tonumber(saved.x) or math.floor((getCore():getScreenWidth() - width) / 2)))
    local y = math.max(0, math.min(maxY,
        tonumber(saved.y) or math.floor((getCore():getScreenHeight() - height) / 2)))
    window = TGSRRChallengeTrackerWindow:new(x, y, width, height)
    window.activeModuleId = saved.tab ~= "" and saved.tab or nil
    window:initialise(); window:addToUIManager()
    TGSRRChallengeTrackerWindow.instance = window
    State.save(window, nil, true)
    return window
end

local function createTracker()
    if not isRatRace() then return end
    if not TGSRRChallengeTrackerWindow.launcher then
        local saved = State.load()
        local maxX = math.max(0, getCore():getScreenWidth() - LAUNCHER_SIZE)
        local maxY = math.max(0, getCore():getScreenHeight() - LAUNCHER_SIZE)
        local x = math.max(0, math.min(maxX, tonumber(saved.launcherX) or LAUNCHER_MARGIN))
        local y = math.max(0, math.min(maxY, tonumber(saved.launcherY) or
            math.floor((getCore():getScreenHeight() - LAUNCHER_SIZE) / 2)))
        local launcher = TGSRRTrackerLauncher:new(x, y, LAUNCHER_SIZE, LAUNCHER_SIZE, "", nil, function()
                local window = TGSRRChallengeTrackerWindow.instance
                if window and window:getIsVisible() then window:close() else TGSRRChallengeTrackerWindow.open() end
            end)
        launcher:initialise()
        launcher:instantiate()
        launcher.imageOff = getTexture(LAUNCHER_TEXTURE_OFF)
        launcher.imageOn = getTexture(LAUNCHER_TEXTURE_ON)
        launcher:setImage(launcher.imageOff)
        launcher:setTooltip(L.text("UI_TGSRR_Tracker_Launcher_Tooltip",
            "Open the Rat Race Challenge Tracker (drag to move)"))
        launcher:setDisplayBackground(false)
        launcher.backgroundColor = { r = 0, g = 0, b = 0, a = 0.65 }
        launcher.backgroundColorMouseOver = { r = 0.16, g = 0.16, b = 0.16, a = 0.9 }
        launcher.borderColor = { r = 0.72, g = 0.72, b = 0.72, a = 0.9 }
        launcher:addToUIManager()
        TGSRRChallengeTrackerWindow.launcher = launcher
    end
    local saved = State.load()
    if saved.open == "true" then TGSRRChallengeTrackerWindow.open() end
end

Events.OnGameStart.Add(createTracker)

return TGSRRChallengeTrackerWindow
