require "ISUI/ISCollapsableWindow"
require "ISUI/ISButton"

local Tracker = require "TGSRR/ChallengeTracker"
local State = require "TGSRR/ChallengeTrackerState"
require "TGSRR/OutpostTrackerModule"

TGSRRChallengeTrackerWindow = ISCollapsableWindow:derive("TGSRRChallengeTrackerWindow")
TGSRRChallengeTrackerWindow.instance = nil
TGSRRChallengeTrackerWindow.launcher = nil

local TAB_HEIGHT = 28
local CONTENT_MARGIN = 6
local HEADER_GAP = 6
local TAB_GAP = 4
local TAB_TEXT_PADDING = 24

local function isRatRace()
    if not getCore():isChallenge() then return false end
    local id = getCore():getChallengeID()
    return id == "TGSRR" or id == "TGSRR_CDDA" or id == "TGSRR_Sprinters"
end

function TGSRRChallengeTrackerWindow:createChildren()
    ISCollapsableWindow.createChildren(self)
    self.tabs = {}
    self.views = {}
    local modules = Tracker.getModules()
    local tabX = CONTENT_MARGIN
    local tabY = self:titleBarHeight() + HEADER_GAP
    for _, module in ipairs(modules) do
        local tabWidth = getTextManager():MeasureStringX(UIFont.Small, module.title) + TAB_TEXT_PADDING
        local button = ISButton:new(tabX, tabY, tabWidth, TAB_HEIGHT, module.title, self, self.onTab)
        button.moduleId = module.id
        button:initialise(); button:instantiate(); self:addChild(button)
        self.tabs[module.id] = button
        tabX = tabX + tabWidth + TAB_GAP

        local contentY = tabY + TAB_HEIGHT + HEADER_GAP
        local contentHeight = self.height - contentY - self:resizeWidgetHeight() - CONTENT_MARGIN
        local view = module.createView(self, CONTENT_MARGIN, contentY,
            self.width - CONTENT_MARGIN * 2, contentHeight)
        view:initialise(); view:instantiate(); view:setVisible(false); self:addChild(view)
        self.views[module.id] = view
    end
    self:selectTab(self.activeModuleId or (modules[1] and modules[1].id))
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
        self.tabs[moduleId].backgroundColor.a = moduleId == id and 0.9 or 0.45
    end
    self.activeModuleId = id
end

function TGSRRChallengeTrackerWindow:onResize()
    ISCollapsableWindow.onResize(self)
    local tabY = self:titleBarHeight() + HEADER_GAP
    local y = tabY + TAB_HEIGHT + HEADER_GAP
    local width = self.width - CONTENT_MARGIN * 2
    local height = self.height - y - self:resizeWidgetHeight() - CONTENT_MARGIN
    local modules = Tracker.getModules()
    local x = CONTENT_MARGIN
    for _, module in ipairs(modules) do
        local tabWidth = getTextManager():MeasureStringX(UIFont.Small, module.title) + TAB_TEXT_PADDING
        local tab = self.tabs and self.tabs[module.id]
        if tab then
            tab:setX(x); tab:setY(tabY); tab:setWidth(tabWidth)
            x = x + tabWidth + TAB_GAP
        end
        local view = self.views and self.views[module.id]
        if view and view.onResize then view:onResize(width, height) end
    end
end

function TGSRRChallengeTrackerWindow:saveState() State.save(self) end
function TGSRRChallengeTrackerWindow:onMouseUp(x, y) ISCollapsableWindow.onMouseUp(self, x, y); self:saveState() end
function TGSRRChallengeTrackerWindow:onMouseUpOutside(x, y) ISCollapsableWindow.onMouseUpOutside(self, x, y); self:saveState() end
function TGSRRChallengeTrackerWindow:close() self:saveState(); self:setVisible(false) end

function TGSRRChallengeTrackerWindow:new(x, y, width, height)
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.title = "The Great Spiffo's Rat Race"
    o.resizable = true
    o.minimumWidth = 430
    o.minimumHeight = 300
    return o
end

function TGSRRChallengeTrackerWindow.open()
    local window = TGSRRChallengeTrackerWindow.instance
    if window then window:setVisible(true); window:addToUIManager(); return window end
    local saved = State.load()
    local width = math.max(430, tonumber(saved.width) or 560)
    local height = math.max(300, tonumber(saved.height) or 590)
    local x = tonumber(saved.x) or math.floor((getCore():getScreenWidth() - width) / 2)
    local y = tonumber(saved.y) or math.floor((getCore():getScreenHeight() - height) / 2)
    window = TGSRRChallengeTrackerWindow:new(x, y, width, height)
    window.activeModuleId = saved.tab ~= "" and saved.tab or nil
    window:initialise(); window:addToUIManager()
    TGSRRChallengeTrackerWindow.instance = window
    return window
end

local function createTracker()
    if not isRatRace() then return end
    if not TGSRRChallengeTrackerWindow.launcher then
        local width, height = 116, 24
        local launcher = ISButton:new(getCore():getScreenWidth() - width - 12, 12, width, height,
            "Rat Race Tracker", nil, function()
                local window = TGSRRChallengeTrackerWindow.instance
                if window and window:getIsVisible() then window:close() else TGSRRChallengeTrackerWindow.open() end
            end)
        launcher:initialise(); launcher:instantiate(); launcher:addToUIManager()
        TGSRRChallengeTrackerWindow.launcher = launcher
    end
    TGSRRChallengeTrackerWindow.open()
end

Events.OnGameStart.Add(createTracker)

return TGSRRChallengeTrackerWindow
