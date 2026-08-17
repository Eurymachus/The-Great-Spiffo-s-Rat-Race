require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local LocationTracker = require "TGSRR/Run/LocationTracker"
local LandmarkMap = require "TGSRR/Tracker/Landmarks/WorldMap"
local L = require "TGSRR/Core/Localization"
local Layout = require "TGSRR/Tracker/Layout"

local View = ISPanel:derive("TGSRRLandmarkTrackerView")
local REFRESH_INTERVAL_MS = 1000
local HEADER_Y = 8
local MARGIN = 8
local LANDMARK_ICON_SIZE = 19
local SCROLL_GUTTER = 18
local LANDMARK_ICON = getTexture("media/ui/LootableMaps/map_asterisk.png")
local function headerHeight() return Layout.boxHeight(UIFont.Small, 7, 28) end
local function footerHeight() return Layout.boxHeight(UIFont.Small, 5, 22) end
local function listTop() return HEADER_Y + headerHeight() end
local function rowHeight() return Layout.rowHeight(LANDMARK_ICON_SIZE) end

local function landmarkRight(width)
    local first = Layout.threeColumns(width)
    return first
end

local function statusLeft(width)
    local _, second = Layout.threeColumns(width)
    return second
end

local function scrollGutter(list)
    return list and list.vscroll and list.vscroll:getWidth() or 0
end

local function snapshotRows(snapshot)
    local rows = {}
    local visited = 0
    for _, entry in ipairs(snapshot.entries or {}) do
        if entry.visited then visited = visited + 1 end
        rows[#rows + 1] = entry
    end
    table.sort(rows, function(a, b)
        if a.visited ~= b.visited then return a.visited == true end
        if a.area ~= b.area then return a.area < b.area end
        return a.name < b.name
    end)
    return rows, visited
end

function View.minimumWidth()
    local rows = snapshotRows(LocationTracker.getSnapshot())
    local names = { L.text("UI_TGSRR_Tracker_Landmark", "Landmark") }
    local areas = { L.text("UI_TGSRR_Tracker_Area", "Area") }
    for _, row in ipairs(rows) do
        names[#names + 1] = row.name
        areas[#areas + 1] = row.area
    end

    local statuses = {
        L.text("UI_TGSRR_Tracker_Status", "Status"),
        L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered"),
        L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered"),
    }
    local first = 30 + Layout.maxTextWidth(UIFont.Small, names) + 8
    local second = Layout.maxTextWidth(UIFont.Small, areas) + 16
    local third = Layout.maxTextWidth(UIFont.Small, statuses) + 16
    return MARGIN * 2 + SCROLL_GUTTER
        + Layout.threeColumnWidth(first, second, third)
end

function View:createChildren()
    ISPanel.createChildren(self)
    local listY = listTop()
    self.list = ISScrollingListBox:new(MARGIN, listY,
        self.width - MARGIN * 2,
        self.height - listY - footerHeight() - MARGIN * 2)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = rowHeight()
    self.list.doDrawItem = self.drawLandmark
    self.list.drawBorder = true
    self.list:setOnMouseDownFunction(self, View.onLocationClicked)
    self:addChild(self.list)
    self:refresh()
end

function View:onLocationClicked(row)
    if not row or not row.anchor then return end
    if self.list:getMouseX() <= landmarkRight(self.list:getWidth()) then
        LandmarkMap.showAt(row.anchor, 0)
    end
end

function View:prerender()
    ISPanel.prerender(self)
    local frameWidth = self.width - MARGIN * 2
    local header = headerHeight()
    local footer = footerHeight()
    self:drawRect(MARGIN, HEADER_Y, frameWidth, header,
        0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(MARGIN, HEADER_Y, frameWidth, header,
        0.7, 0.65, 0.65, 0.65)
    local textY = HEADER_Y + math.floor(
        (header - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawText(L.text("UI_TGSRR_Tracker_Landmark", "Landmark"),
        MARGIN + 8, textY, 1, 1, 1, 1, UIFont.Small)
    local columnWidth = frameWidth - scrollGutter(self.list)
    local landmarkX = landmarkRight(columnWidth)
    local statusX = statusLeft(columnWidth)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Area", "Area"),
        MARGIN + landmarkX + math.floor((statusX - landmarkX) / 2), textY,
        1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Status", "Status"),
        MARGIN + statusX + math.floor((frameWidth - statusX) / 2), textY,
        1, 1, 1, 1, UIFont.Small)

    local footerY = self.height - MARGIN - footer
    self:drawRect(MARGIN, footerY, frameWidth, footer,
        0.8, 0.02, 0.02, 0.02)
    local total = self.total or 0
    local visited = self.visited or 0
    if total > 0 and visited > 0 then
        self:drawRect(MARGIN + 1, footerY + 1,
            math.floor((frameWidth - 2) * visited / total), footer - 2,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(MARGIN, footerY, frameWidth, footer,
        0.62, 0.55, 0.55, 0.55)
    self:drawTextCentre(tostring(visited) .. " "
            .. L.text("UI_TGSRR_Tracker_Of", "of") .. " " .. tostring(total)
            .. " " .. L.text("UI_TGSRR_Tracker_LandmarksDiscovered",
                "landmarks discovered"),
        MARGIN + frameWidth / 2,
        footerY + math.floor((footer - Layout.lineHeight(UIFont.Small)) / 2),
        1, 1, 1, 1, UIFont.Small)
end

function View:drawLandmark(y, item, alt)
    local row = item.item
    local width = self:getWidth()
    local contentWidth = width - scrollGutter(self)
    if item.index % 2 == 0 then
        self:drawRect(0, y, width, self.itemheight - 1,
            0.18, 0.12, 0.12, 0.12)
    end
    self:drawRect(0, y + self.itemheight - 1, width, 1,
        0.3, 0.5, 0.5, 0.5)
    local textY = y + math.floor(
        (self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local color = row.visited and { 0.35, 1, 0.45 } or { 0.62, 0.62, 0.62 }
    if LANDMARK_ICON then
        self:drawTextureScaledAspect(LANDMARK_ICON, 6,
            y + math.floor((self.itemheight - LANDMARK_ICON_SIZE) / 2),
            LANDMARK_ICON_SIZE, LANDMARK_ICON_SIZE, 1,
            color[1], color[2], color[3])
    end
    self:drawText(row.name, LANDMARK_ICON and 30 or 8, textY,
        color[1], color[2], color[3], 1, UIFont.Small)
    local landmarkX = landmarkRight(contentWidth)
    local statusX = statusLeft(contentWidth)
    self:drawTextCentre(row.area,
        landmarkX + math.floor((statusX - landmarkX) / 2), textY,
        0.8, 0.8, 0.8, 1, UIFont.Small)
    self:drawTextCentre(row.visited
            and L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered")
            or L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered"),
        statusX + math.floor((contentWidth - statusX) / 2), textY,
        color[1], color[2], color[3], 1, UIFont.Small)
    return y + self.itemheight
end

function View:refresh()
    if not self.list then return end
    local snapshot = LocationTracker.getSnapshot()
    local rows, visited = snapshotRows(snapshot)
    self.visited = visited
    self.total = #rows
    self.list:clear()
    for _, row in ipairs(rows) do
        local tooltip = row.name .. "\n" .. row.area .. "\n" .. row.category
        if row.firstVisit then
            tooltip = tooltip .. "\nBuilding ID: "
                .. tostring(row.firstVisit.buildingId)
        end
        self.list:addItem(row.name, row, tooltip)
    end
    self.lastRefreshMs = getTimestampMs()
end

function View:update()
    ISPanel.update(self)
    if not self:getIsVisible() then return end
    local now = getTimestampMs()
    if not self.lastRefreshMs
            or now - self.lastRefreshMs >= REFRESH_INTERVAL_MS then
        self:refresh()
    end
end

function View:onShow()
    self:setVisible(true)
    self:refresh()
end

function View:onHide()
    self:setVisible(false)
end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
    if self.list then
        local listY = listTop()
        self.list:setWidth(width - MARGIN * 2)
        self.list:setHeight(height - listY - footerHeight() - MARGIN * 2)
    end
end

function View:new(x, y, width, height)
    local view = ISPanel.new(self, x, y, width, height)
    view.background = false
    return view
end

return View
