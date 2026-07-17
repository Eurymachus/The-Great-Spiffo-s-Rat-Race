require "ISUI/ISCollapsableWindow"
require "ISUI/ISScrollingListBox"

local Snapshot = require "TGSRR/OutpostTrackerSnapshot"
local L = require "TGSRR/Localization"
local Icons = require "TGSRR/OutpostIcons"

local Window = ISCollapsableWindow:derive("TGSRROutpostOverviewWindow")
Window.instance = nil

local WIDTH = 640
local HEIGHT = 650
local MARGIN = 12
local HEADER_HEIGHT = 112
local COLUMN_VALUE_X = 0.58
local COLUMN_STATUS_X = 0.80
local REFRESH_INTERVAL_MS = 1000
local STATE_FILE = "TGSRR/OutpostOverviewWindow.ini"

local function loadWindowState()
    local reader = getFileReader(STATE_FILE, false)
    if not reader then return nil end
    local state = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local key, value = line:match("^%s*(.-)%s*=%s*(.-)%s*$")
        if key then state[key] = tonumber(value) end
    end
    reader:close()
    if not state.x or not state.y then return nil end
    return state
end

local function saveWindowState(window)
    local writer = getFileWriter(STATE_FILE, true, false)
    if not writer then return end
    writer:write("x=" .. tostring(math.floor(window:getX())) .. "\n")
    writer:write("y=" .. tostring(math.floor(window:getY())) .. "\n")
    writer:close()
end

local function statusText(status)
    if status == "passed" then return L.text("UI_TGSRR_Tracker_Passed", "Passed") end
    if status == "pending" then return L.text("UI_TGSRR_Tracker_Pending", "Pending") end
    return L.text("UI_TGSRR_Tracker_Unavailable", "Unavailable")
end

local function requirement(labelKey, fallback, tooltipKey, tooltipFallback, value, status)
    return {
        label = L.text(labelKey, fallback),
        tooltip = L.text(tooltipKey, tooltipFallback),
        value = value or "-",
        status = status or "unavailable",
    }
end

local function buildRequirements(row)
    local activation = row.activation
    local runtime = row.runtime or {}
    local deliverables = runtime.deliverables or {}
    local clearance = deliverables.zombie_clearance
    local windows = deliverables.window_barricades
    local enclosed = deliverables.enclosed
    local doorsFitted = deliverables.doors_fitted
    local doorsClosed = deliverables.doors_closed
    local discovered = runtime.discovered == true
    local activationPassed = activation and activation.passed == true
    local clearanceValue = clearance and
        (tostring(clearance.current) .. " " ..
            L.text("UI_TGSRR_Tracker_RemainingLower", "remaining")) or "-"
    local windowValue = windows and
        (tostring(windows.current) .. " / " .. tostring(windows.required)) or "-"
    local enclosedValue = enclosed and
        (tostring(enclosed.current) .. " / " .. tostring(enclosed.required)) or "-"
    local doorsFittedValue = doorsFitted and
        (tostring(doorsFitted.current) .. " / " .. tostring(doorsFitted.required)) or "-"
    local doorsValue = doorsClosed and
        (tostring(doorsClosed.current) .. " / " .. tostring(doorsClosed.required)) or "-"

    return {
        requirement("UI_TGSRR_Tracker_Discovery", "Discovery",
            "UI_TGSRR_Tracker_Tooltip_Discovery", "Enter the outpost's 150 x 150 clearance area.", nil,
            discovered and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_RoomActivation", "Room activation",
            "UI_TGSRR_Tracker_Tooltip_RoomActivation", "Visit every required accessible room in the outpost.",
            activation and (tostring(activation.activatedRooms) .. " / " .. tostring(activation.totalRooms)) or "-",
            activationPassed and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_FloorActivation", "Floor activation",
            "UI_TGSRR_Tracker_Tooltip_FloorActivation", "Activate every required floor, including registered basements.",
            activation and (tostring(activation.activatedFloors) .. " / " .. tostring(activation.totalFloors)) or "-",
            activationPassed and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_ZombieClearance", "Zombie clearance",
            "UI_TGSRR_Tracker_Tooltip_ZombieClearance", "Clear the live zombies within the outpost's 150 x 150 clearance area.",
            clearanceValue, clearance and (clearance.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_WindowBarricades", "Window barricades",
            "UI_TGSRR_Tracker_Tooltip_WindowBarricades", "Barricade every ground-floor exterior window with wood, sheet metal, or metal bars.",
            windowValue, windows and (windows.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_ExteriorWalls", "Enclosed",
            "UI_TGSRR_Tracker_Tooltip_Enclosed", "Seal every ground-floor exterior edge with a wall, window opening, or doorway containing a door.",
            enclosedValue, enclosed and (enclosed.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_DoorsFitted", "Doors fitted",
            "UI_TGSRR_Tracker_Tooltip_DoorsFitted", "Fit a door into every ground-floor exterior door frame.",
            doorsFittedValue, doorsFitted and (doorsFitted.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_ExteriorDoors", "Doors closed",
            "UI_TGSRR_Tracker_Tooltip_DoorsClosed", "Close every ground-floor exterior door. Missing doors cannot pass.",
            doorsValue, doorsClosed and (doorsClosed.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_GoodBed", "Good bed",
            "UI_TGSRR_Tracker_Tooltip_GoodBed", "Provide a qualifying good bed within the outpost."),
        requirement("UI_TGSRR_Tracker_Power", "Power",
            "UI_TGSRR_Tracker_Tooltip_Power", "Provide a qualifying source of electrical power for the outpost."),
        requirement("UI_TGSRR_Tracker_Food", "5,000 calories of food",
            "UI_TGSRR_Tracker_Tooltip_Food", "Store at least 5,000 qualifying calories of food at the outpost."),
        requirement("UI_TGSRR_Tracker_PlumbedSink", "Plumbed sink",
            "UI_TGSRR_Tracker_Tooltip_PlumbedSink", "Provide a qualifying plumbed sink within the outpost."),
        requirement("UI_TGSRR_Tracker_SpareCar", "Spare car",
            "UI_TGSRR_Tracker_Tooltip_SpareCar", "Park a qualifying spare car within the outpost's support area."),
    }
end

local function findRow(outpost)
    local snapshot = Snapshot.getAll(getSpecificPlayer(0) or getPlayer())
    for _, row in ipairs(snapshot.rows) do
        if row.id == outpost.id then return row end
    end
    return nil
end

function Window:createChildren()
    ISCollapsableWindow.createChildren(self)
    local top = self:titleBarHeight() + HEADER_HEIGHT
    self.list = ISScrollingListBox:new(MARGIN, top, self.width - MARGIN * 2,
        self.height - top - MARGIN)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = 36
    self.list.doDrawItem = self.drawRequirement
    self.list.drawBorder = true
    self:addChild(self.list)
    self:refresh()
end

function Window:prerender()
    ISCollapsableWindow.prerender(self)
    if not self.row then return end

    local top = self:titleBarHeight() + 10
    local icon = Icons.get(self.row.outpost)
    local iconR, iconG, iconB = Icons.getColor(self.row.status, self.row.complete)
    if icon then self:drawTextureScaledAspect(icon, MARGIN, top, 54, 54, 1, iconR, iconG, iconB) end

    self:drawText(self.row.title, 78, top + 2, 1, 1, 1, 1, UIFont.Large)
    local stage = self.row.complete and L.text("UI_TGSRR_Tracker_Stage_Complete", "Complete") or
        (self.row.status == "undiscovered" and
            L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered") or
            L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered"))
    self:drawText(L.text("UI_TGSRR_Tracker_Stage", "Stage") .. ": " .. stage,
        78, top + 34, 0.76, 0.76, 0.76, 1, UIFont.Small)

    local barX, barY = MARGIN, top + 68
    local barWidth = self.width - MARGIN * 2
    self:drawRect(barX, barY, barWidth, 22, 0.8, 0.02, 0.02, 0.02)
    if self.row.percent > 0 then
        self:drawRect(barX + 1, barY + 1,
            math.floor((barWidth - 2) * self.row.percent / 100), 20,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(barX, barY, barWidth, 22, 0.62, 0.55, 0.55, 0.55)
    local progressTextY = barY + math.floor((22 - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Progress", "Progress") .. ": " ..
        tostring(self.row.percent) .. "%", barX + barWidth / 2, progressTextY,
        1, 1, 1, 1, UIFont.Small)
end

function Window:drawRequirement(y, item, alt)
    local data = item.item
    local width = self:getWidth() - (self:isVScrollBarVisible() and self.vscroll:getWidth() or 0)
    if item.index % 2 == 0 then self:drawRect(0, y, width, self.itemheight - 1, 0.2, 0.12, 0.12, 0.12) end
    self:drawRect(0, y + self.itemheight - 1, width, 1, 0.32, 0.5, 0.5, 0.5)
    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawText(data.label, 8, textY, 1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(data.value, math.floor(width * (COLUMN_VALUE_X + COLUMN_STATUS_X) / 2),
        textY, 0.82, 0.82, 0.82, 1, UIFont.Small)
    local colors = { passed = { 0.42, 0.9, 0.48 }, pending = { 1, 0.75, 0.24 },
        unavailable = { 0.55, 0.55, 0.55 } }
    local color = colors[data.status] or colors.unavailable
    self:drawTextCentre(statusText(data.status), math.floor(width * (COLUMN_STATUS_X + 1) / 2),
        textY, color[1], color[2], color[3], 1, UIFont.Small)
    return y + self.itemheight
end

function Window:refresh()
    self.row = self.outpost and findRow(self.outpost) or nil
    if not self.row or not self.list then return end
    local requirements = buildRequirements(self.row)
    if #self.list.items ~= #requirements then
        self.list:clear()
        for _, entry in ipairs(requirements) do self.list:addItem(entry.label, entry, entry.tooltip) end
    else
        for index, entry in ipairs(requirements) do
            self.list.items[index].text = entry.label
            self.list.items[index].item = entry
            self.list.items[index].tooltip = entry.tooltip
        end
    end
    self.lastRefreshMs = getTimestampMs()
end

function Window:update()
    ISCollapsableWindow.update(self)
    if not self:getIsVisible() then return end
    local now = getTimestampMs()
    if not self.lastRefreshMs or now - self.lastRefreshMs >= REFRESH_INTERVAL_MS then self:refresh() end
end

function Window:close()
    saveWindowState(self)
    self:setVisible(false)
end

function Window:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    saveWindowState(self)
end

function Window:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    saveWindowState(self)
end

function Window:new(x, y, width, height, outpost)
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.title = L.text("UI_TGSRR_Tracker_OutpostOverview", "Outpost Overview")
    o.outpost = outpost
    o.resizable = false
    o:setResizable(false)
    return o
end

function Window.showFor(outpost)
    local window = Window.instance
    if not window then
        local width = math.min(WIDTH, getCore():getScreenWidth())
        local height = math.min(HEIGHT, getCore():getScreenHeight())
        local state = loadWindowState()
        local x = state and state.x or math.floor((getCore():getScreenWidth() - width) / 2)
        local y = state and state.y or math.floor((getCore():getScreenHeight() - height) / 2)
        x = math.max(0, math.min(x, getCore():getScreenWidth() - width))
        y = math.max(0, math.min(y, getCore():getScreenHeight() - height))
        window = Window:new(x, y, width, height, outpost)
        window:initialise()
        Window.instance = window
    else
        window.outpost = outpost
        window:refresh()
    end
    window:addToUIManager()
    window:setVisible(true)
    window:bringToTop()
    return window
end

return Window
