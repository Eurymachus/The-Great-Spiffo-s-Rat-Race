require "ISUI/ISCollapsableWindow"
require "ISUI/ISButton"

local Tracker = require "TGSRR/ChallengeTracker"
local State = require "TGSRR/ChallengeTrackerState"
local L = require "TGSRR/Localization"
require "TGSRR/OverviewTrackerModule"
require "TGSRR/KillsTrackerModule"
require "TGSRR/SkillsTrackerModule"
require "TGSRR/OutpostTrackerModule"

TGSRRChallengeTrackerWindow = ISCollapsableWindow:derive("TGSRRChallengeTrackerWindow")
TGSRRChallengeTrackerWindow.instance = nil
TGSRRChallengeTrackerWindow.launcher = nil

local TAB_HEIGHT = 28
local TAB_WIDTH = 100
local CONTENT_MARGIN = 6
local WINDOW_WIDTH = 800
local WINDOW_HEIGHT = 650
local LAUNCHER_SIZE = 58
local LAUNCHER_MARGIN = 4
local LAUNCHER_TEXTURE = "Item_DeadRat.png"
local LAUNCHER_ICON_SIZE = LAUNCHER_SIZE - 8
local LAUNCHER_STROKE_OFFSETS = {
    { -1, -1 }, { 0, -1 }, { 1, -1 },
    { -1,  0 },            { 1,  0 },
    { -1,  1 }, { 0,  1 }, { 1,  1 },
}
local DRAG_THRESHOLD = 4

local TGSRRTrackerLauncher = ISButton:derive("TGSRRTrackerLauncher")

function TGSRRTrackerLauncher:render()
    local image = self.image
    self.image = nil
    ISButton.render(self)
    self.image = image
    if not image then return end

    local x = (self.width - LAUNCHER_ICON_SIZE) / 2
    local y = (self.height - LAUNCHER_ICON_SIZE) / 2
    local alpha = self.textureColor.a
    local intensity = (self.mouseOver or self.pressed) and 1 or 0.65
    for _, offset in ipairs(LAUNCHER_STROKE_OFFSETS) do
        self:drawTextureScaledAspect(image, x + offset[1], y + offset[2],
            LAUNCHER_ICON_SIZE, LAUNCHER_ICON_SIZE, alpha, 0, 0, 0)
    end
    self:drawTextureScaledAspect(image, x, y, LAUNCHER_ICON_SIZE, LAUNCHER_ICON_SIZE,
        alpha, self.textureColor.r * intensity, self.textureColor.g * intensity,
        self.textureColor.b * intensity)
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
    if not getCore():isChallenge() then return false end
    local id = getCore():getChallengeID()
    return id == "TGSRR" or id == "TGSRR_CDDA" or id == "TGSRR_Sprinters"
end

function TGSRRChallengeTrackerWindow:createChildren()
    ISCollapsableWindow.createChildren(self)
    self.tabs = {}
    self.views = {}
    local tabY = self:titleBarHeight()
    self.tabPanel = ISPanel:new(0, tabY, self.width, TAB_HEIGHT)
    self.tabPanel:initialise()
    self.tabPanel.backgroundColor = { r = 0, g = 0, b = 0, a = 0.65 }
    self:addChild(self.tabPanel)

    local modules = Tracker.getModules()
    for index, module in ipairs(modules) do
        local button = ISButton:new((index - 1) * TAB_WIDTH, 0, TAB_WIDTH, TAB_HEIGHT,
            module.title, self, self.onTab)
        button.moduleId = module.id
        button:initialise(); button:instantiate(); self.tabPanel:addChild(button)
        self.tabs[module.id] = button

        local contentY = tabY + TAB_HEIGHT
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
    local y = tabY + TAB_HEIGHT
    local width = self.width - CONTENT_MARGIN * 2
    local height = self.height - y - CONTENT_MARGIN
    if self.tabPanel then
        self.tabPanel:setY(tabY)
        self.tabPanel:setWidth(self.width)
    end
    local modules = Tracker.getModules()
    for index, module in ipairs(modules) do
        local tab = self.tabs and self.tabs[module.id]
        if tab then
            tab:setX((index - 1) * TAB_WIDTH); tab:setY(0); tab:setWidth(TAB_WIDTH)
        end
        local view = self.views and self.views[module.id]
        if view and view.onResize then view:onResize(width, height) end
    end
end

function TGSRRChallengeTrackerWindow:saveState() State.save(self, nil, self:getIsVisible()) end
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
    local width = WINDOW_WIDTH
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
        launcher:setImage(getTexture(LAUNCHER_TEXTURE))
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
