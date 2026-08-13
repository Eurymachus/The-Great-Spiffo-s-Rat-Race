require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Snapshot = require "TGSRR/Tracker/Outposts/Snapshot"
local L = require "TGSRR/Core/Localization"
local Icons = require "TGSRR/Tracker/Outposts/Icons"
local Notifications = require "TGSRR/Challenge/Notifications"
local Overview = require "TGSRR/Tracker/Outposts/OverviewWindow"
local Layout = require "TGSRR/Tracker/Layout"

local View = ISPanel:derive("TGSRROutpostTrackerView")
local REFRESH_INTERVAL_MS = 1000
local HEADER_Y = 8
local MARGIN = 8
local OUTPOST_ICON_SIZE = 19
local function headerHeight() return Layout.boxHeight(UIFont.Small, 7, 28) end
local function footerHeight() return Layout.boxHeight(UIFont.Small, 5, 22) end
local function listTop() return HEADER_Y + headerHeight() end
local function rowHeight() return Layout.rowHeight(OUTPOST_ICON_SIZE) end

local function outpostRight(width)
    local first = Layout.threeColumns(width)
    return first
end

local function progressLeft(width)
    local _, second = Layout.threeColumns(width)
    return second
end

local function scrollGutter(list)
    return list and list.vscroll and list.vscroll:getWidth() or 0
end

function View:createChildren()
    ISPanel.createChildren(self)
    local listY = listTop()
    self.list = ISScrollingListBox:new(MARGIN, listY, self.width - MARGIN * 2,
        self.height - listY - footerHeight() - MARGIN * 2)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = rowHeight()
    self.list.doDrawItem = self.drawOutpost
    self.list.drawBorder = true
    self.list:setOnMouseDoubleClick(self, View.onActivate)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:prerender()
    ISPanel.prerender(self)
    local x = 8
    local frameWidth = self.width - 16
    local header = headerHeight()
    local footer = footerHeight()
    self:drawRect(x, HEADER_Y, frameWidth, header, 0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(x, HEADER_Y, frameWidth, header, 0.7, 0.65, 0.65, 0.65)

    local textY = HEADER_Y + math.floor((header - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawText(L.text("UI_TGSRR_Tracker_Outpost", "Outpost"),
        x + 8, textY, 1, 1, 1, 1, UIFont.Small)
    local headers = {
        L.text("UI_TGSRR_Tracker_Stage", "Stage"),
        L.text("UI_TGSRR_Tracker_Progress", "Progress"),
    }
    local columnWidth = frameWidth - scrollGutter(self.list)
    local stageLeft = outpostRight(columnWidth)
    local progressX = progressLeft(columnWidth)
    self:drawTextCentre(headers[1], x + stageLeft + math.floor((progressX - stageLeft) / 2),
        textY, 1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(headers[2], x + progressX + math.floor((frameWidth - progressX) / 2),
        textY, 1, 1, 1, 1, UIFont.Small)

    local footerY = self.height - MARGIN - footer
    self:drawRect(x, footerY, frameWidth, footer, 0.8, 0.02, 0.02, 0.02)
    local snapshot = self.snapshot
    local percent = snapshot and snapshot.percent or 0
    if percent > 0 then
        self:drawRect(x + 1, footerY + 1,
            math.floor((frameWidth - 2) * percent / 100), footer - 2,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(x, footerY, frameWidth, footer, 0.62, 0.55, 0.55, 0.55)
    local footerTextY = footerY + math.floor((footer - Layout.lineHeight(UIFont.Small)) / 2)
    local completed = snapshot and snapshot.completed or 0
    local total = snapshot and #snapshot.rows or 0
    local footerText = tostring(completed) .. " " .. L.text("UI_TGSRR_Tracker_Of", "of") .. " " ..
        tostring(total) .. " (" .. string.format("%.1f%%", percent) .. ")"
    self:drawTextCentre(footerText, x + frameWidth / 2, footerTextY, 1, 1, 1, 1, UIFont.Small)
end

function View:drawOutpost(y, item, alt)
    local data = item.item
    local rowWidth = self:getWidth()
    local contentWidth = rowWidth - scrollGutter(self)
    local hovered = self.mouseoverselected == item.index
    if item.index % 2 == 0 then self:drawRect(0, y, rowWidth, self.itemheight - 1, 0.18, 0.12, 0.12, 0.12) end
    if hovered then self:drawRect(0, y, rowWidth, self.itemheight - 1, 0.4, 0.28, 0.28, 0.28) end
    self:drawRect(0, y + self.itemheight - 1, rowWidth, 1, 0.35, 0.6, 0.6, 0.6)

    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local colors = {
        undiscovered = { 0.58, 0.58, 0.58 },
        discovered = { 1, 1, 1 },
        in_progress = { 1, 0.78, 0.18 },
        complete = { 0.35, 1, 0.45 },
    }
    local statusColor = data.complete and colors.complete or (colors[data.status] or colors.discovered)
    local labelColor = data.status == "undiscovered" and colors.undiscovered or colors.discovered
    local icon = Icons.get(data.outpost)
    local iconR, iconG, iconB = Icons.getColor(data.status, data.complete)
    if icon then
        self:drawTextureScaledAspect(icon, 6,
            y + math.floor((self.itemheight - OUTPOST_ICON_SIZE) / 2),
            OUTPOST_ICON_SIZE, OUTPOST_ICON_SIZE, 1,
            iconR, iconG, iconB)
    end
    self:drawText(data.title, 30, textY,
        labelColor[1], labelColor[2], labelColor[3], 1, UIFont.Small)
    local stage = data.complete and L.text("UI_TGSRR_Tracker_Stage_Complete", "Complete") or
        (data.status == "in_progress" and L.text("UI_TGSRR_Tracker_Stage_InProgress", "In Progress") or
        (data.status == "undiscovered" and
            L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered") or
            L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered")))
    local stageLeft = outpostRight(contentWidth)
    local progressX = progressLeft(contentWidth)
    self:drawTextCentre(stage,
        stageLeft + math.floor((progressX - stageLeft) / 2), textY,
        statusColor[1], statusColor[2], statusColor[3], 1, UIFont.Small)

    local padding = Layout.columnPadding()
    local progressBarX = progressX + padding
    local progressWidth = math.max(1, contentWidth - progressBarX - padding)
    local progressHeight = Layout.progressBarHeight()
    local progressY = y + math.floor((self.itemheight - progressHeight) / 2)
    self:drawRect(progressBarX, progressY, progressWidth, progressHeight, 0.8, 0.02, 0.02, 0.02)
    if data.percent > 0 then
        self:drawRect(progressBarX + 1, progressY + 1,
            math.floor((progressWidth - 2) * data.percent / 100), progressHeight - 2,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(progressBarX, progressY, progressWidth, progressHeight, 0.62, 0.55, 0.55, 0.55)
    self:drawTextCentre(data.requirements .. " (" .. tostring(data.percent) .. "%)",
        progressBarX + math.floor(progressWidth / 2), textY,
        labelColor[1], labelColor[2], labelColor[3], 1, UIFont.Small)
    return y + self.itemheight
end

local function buildTooltip(outpost, activation, percent, runtime, status)
    local lines = {
        L.text(outpost.nameKey, outpost.name),
        L.text("UI_TGSRR_Tracker_Stage", "Stage") .. ": " ..
            (status == "complete" and L.text("UI_TGSRR_Tracker_Stage_Complete", "Complete") or
            (status == "in_progress" and L.text("UI_TGSRR_Tracker_Stage_InProgress", "In Progress") or
            (status == "undiscovered" and
                L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered") or
                L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered")))),
        L.text("UI_TGSRR_Tracker_Progress", "Progress") .. ": " .. tostring(percent) .. "%",
    }
    if activation then
        lines[#lines + 1] = L.text("UI_TGSRR_Tracker_RoomsActivated", "Rooms activated") ..
            ": " .. activation.activatedRooms .. " / " .. activation.totalRooms
        lines[#lines + 1] = L.text("UI_TGSRR_Tracker_FloorsActivated", "Floors activated") ..
            ": " .. activation.activatedFloors .. " / " .. activation.totalFloors
        if activation.loadedRooms ~= nil then
            lines[#lines + 1] = L.text("UI_TGSRR_Tracker_RoomsLoaded", "Rooms currently loaded") ..
                ": " .. activation.loadedRooms .. " / " .. activation.totalRooms
        end
    else
        lines[#lines + 1] = L.text("UI_TGSRR_Tracker_OutpostNotEvaluated",
            "Outpost data has not been evaluated.")
    end
    if runtime and runtime.discovered then
        local clearance = runtime.deliverables and runtime.deliverables.zombie_clearance or nil
        lines[#lines + 1] = L.text("UI_TGSRR_Tracker_AreaCleared", "Area Cleared") .. ": " ..
            (clearance and clearance.passed and L.text("UI_TGSRR_Tracker_Yes", "Yes") or
                L.text("UI_TGSRR_Tracker_No", "No"))
    end
    lines[#lines + 1] = L.text("UI_TGSRR_Tracker_DoubleClickDetails", "Double-click for details")
    return table.concat(lines, "\n")
end

function View:refresh(player)
    if not self.list then return end
    local snapshot = Snapshot.getAll(player)
    self.snapshot = snapshot
    local rebuild = #self.list.items ~= #snapshot.rows
    if not rebuild then
        for index, row in ipairs(snapshot.rows) do
            if self.list.items[index].item.id ~= row.id then rebuild = true; break end
        end
    end

    if rebuild then
        local selectedId = self.list.items[self.list.selected] and self.list.items[self.list.selected].item.id or nil
        local scrollY = self.list:getYScroll()
        self.list:clear()
        for _, row in ipairs(snapshot.rows) do
            local item = self.list:addItem(row.title, row,
                buildTooltip(row.outpost, row.activation, row.percent, row.runtime, row.status))
            if selectedId == row.id then self.list.selected = item.itemindex end
        end
        self.list:setYScroll(scrollY)
    else
        for index, row in ipairs(snapshot.rows) do
            local item = self.list.items[index]
            item.text = row.title
            item.item = row
            item.tooltip = buildTooltip(row.outpost, row.activation, row.percent, row.runtime, row.status)
        end
    end
    self.lastRefreshMs = getTimestampMs()
end

function View:update()
    ISPanel.update(self)
    if not self:getIsVisible() then return end
    local now = getTimestampMs()
    if not self.lastRefreshMs or now - self.lastRefreshMs >= REFRESH_INTERVAL_MS then
        self:refresh(getSpecificPlayer(0) or getPlayer())
    end
end

function View:onActivate(item)
    if not item then return end
    Overview.showFor(item.outpost)
end

function View:onShow()
    self:setVisible(true)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:onHide() self:setVisible(false) end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
    if self.list then
        self.list:setWidth(width - MARGIN * 2)
        self.list:setY(listTop())
        self.list:setHeight(height - listTop() - footerHeight() - MARGIN * 2)
        self.list.vscroll:bringToTop()
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    View.instance = o
    return o
end

Notifications.subscribe("outpost-tracker-view", function()
    local view = View.instance
    if view and view:getIsVisible() then view:refresh(getSpecificPlayer(0) or getPlayer()) end
end)

return View
