require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local KillsData = require "TGSRR/Tracker/Kills/Data"
local L = require "TGSRR/Core/Localization"
local Layout = require "TGSRR/Tracker/Layout"

local View = ISPanel:derive("TGSRRKillsTrackerView")
local TARGET_KILLS = 1000000
local MARGIN = 8
local HEADER_Y = 8
local MILESTONE_ICON_SIZE = 19
local MILESTONE_ICON = getTexture("media/ui/LootableMaps/map_skull.png")

local function headerHeight() return Layout.boxHeight(UIFont.Small, 7, 28) end
local function footerHeight() return Layout.boxHeight(UIFont.Small, 5, 22) end
local function listTop() return HEADER_Y + headerHeight() end
local function rowHeight() return Layout.rowHeight(MILESTONE_ICON_SIZE) end

local function milestoneRight(width)
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

local function commaValue(value)
    local text = tostring(math.max(0, math.floor(tonumber(value) or 0)))
    while true do
        local replaced
        text, replaced = text:gsub("^(-?%d+)(%d%d%d)", "%1,%2")
        if replaced == 0 then return text end
    end
end

local function clamp(value)
    return math.max(0, math.min(1, tonumber(value) or 0))
end

local function percentValue(progress)
    local percent = clamp(progress) * 100
    if percent == 0 then return "0" end
    local decimals = 1
    if percent < 0.001 then
        decimals = 4
    elseif percent < 0.01 then
        decimals = 3
    elseif percent < 0.1 then
        decimals = 2
    end
    return string.format("%." .. tostring(decimals) .. "f", percent)
        :gsub("0+$", ""):gsub("%.$", "")
end

function View:createChildren()
    ISPanel.createChildren(self)
    self.list = ISScrollingListBox:new(MARGIN, listTop(), self.width - MARGIN * 2,
        self.height - listTop() - footerHeight() - MARGIN * 2)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = rowHeight()
    self.list.doDrawItem = self.drawMilestone
    self.list.drawBorder = true
    self.list.backgroundColor = { r = 0, g = 0, b = 0, a = 0.35 }
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:refresh(player)
    local record = KillsData.refresh(player)
    self.playerAvailable = record.available
    self.current = record.current or 0
    self.percent = record.percent
    if not self.list then return end

    local previousThreshold = 0
    local milestones = KillsData.getMilestones()
    if #self.list.items ~= #milestones then
        self.list:clear()
        for _, threshold in ipairs(milestones) do
            self.list:addItem(commaValue(threshold), { threshold = threshold })
        end
    end
    for index, threshold in ipairs(milestones) do
        local data = self.list.items[index].item
        data.threshold = threshold
        data.previousThreshold = previousThreshold
        data.reached = self.current >= threshold
        data.current = self.current
        data.active = not data.reached and self.current >= previousThreshold
        if data.reached then
            data.progress = 1
        elseif data.active then
            data.progress = clamp(self.current / threshold)
        else
            data.progress = 0
        end
        previousThreshold = threshold
    end
end

function View:prerender()
    ISPanel.prerender(self)
    local record = KillsData.getRecord()
    if (record.current or 0) ~= self.current or record.available ~= self.playerAvailable then
        self:refresh(getSpecificPlayer(0) or getPlayer())
    end
    self.playerAvailable = record.available
    self.current = record.current or 0
    self.percent = record.percent

    local frameWidth = self.width - MARGIN * 2
    local goalHeight = footerHeight()
    local header = headerHeight()
    local goalBarY = self.height - MARGIN - goalHeight
    self:drawRect(MARGIN, goalBarY, frameWidth, goalHeight, 0.8, 0.02, 0.02, 0.02)
    if self.percent > 0 then
        self:drawRect(MARGIN + 1, goalBarY + 1, math.floor((frameWidth - 2) * self.percent / 100),
            goalHeight - 2, 0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(MARGIN, goalBarY, frameWidth, goalHeight, 0.62, 0.55, 0.55, 0.55)
    local textY = goalBarY + math.floor((goalHeight - Layout.lineHeight(UIFont.Small)) / 2)
    local progressText = self.playerAvailable and
        (commaValue(self.current) .. " " .. L.text("UI_TGSRR_Tracker_Of", "of") .. " " ..
            commaValue(TARGET_KILLS) .. " (" .. percentValue(self.percent / 100) .. "%)") or
        L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable.")
    self:drawTextCentre(progressText, MARGIN + frameWidth / 2, textY, 1, 1, 1, 1, UIFont.Small)

    self:drawRect(MARGIN, HEADER_Y, frameWidth, header, 0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(MARGIN, HEADER_Y, frameWidth, header, 0.7, 0.65, 0.65, 0.65)
    local headerTextY = HEADER_Y + math.floor((header - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawText(L.text("UI_TGSRR_Tracker_Milestone", "Milestone"),
        MARGIN + 8, headerTextY, 1, 1, 1, 1, UIFont.Small)
    local headers = {
        L.text("UI_TGSRR_Tracker_Status", "Status"),
        L.text("UI_TGSRR_Tracker_Progress", "Progress"),
    }
    local columnWidth = frameWidth - scrollGutter(self.list)
    local statusLeft = milestoneRight(columnWidth)
    local progressX = progressLeft(columnWidth)
    self:drawTextCentre(headers[1], MARGIN + statusLeft + math.floor((progressX - statusLeft) / 2),
        headerTextY, 1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(headers[2], MARGIN + progressX + math.floor((frameWidth - progressX) / 2),
        headerTextY, 1, 1, 1, 1, UIFont.Small)
end

function View:drawMilestone(y, item, alt)
    local data = item.item
    local rowWidth = self:getWidth()
    local contentWidth = rowWidth - scrollGutter(self)
    if item.index % 2 == 0 then self:drawRect(0, y, rowWidth, self.itemheight - 1, 0.18, 0.12, 0.12, 0.12) end
    self:drawRect(0, y + self.itemheight - 1, rowWidth, 1, 0.3, 0.5, 0.5, 0.5)

    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local status = L.text("UI_TGSRR_Tracker_MilestoneLocked", "Locked")
    local r, g, b = 0.58, 0.58, 0.58
    if data.reached then
        status = L.text("UI_TGSRR_Tracker_MilestoneReached", "Reached")
        r, g, b = 0.35, 1, 0.45
    elseif data.active then
        status = L.text("UI_TGSRR_Tracker_MilestoneNext", "Next")
        r, g, b = 1, 0.78, 0.18
    end
    local labelColor = (data.active or data.reached) and { 1, 1, 1 } or { 0.58, 0.58, 0.58 }
    if MILESTONE_ICON then
        self:drawTextureScaledAspect(MILESTONE_ICON, 6,
            y + math.floor((self.itemheight - MILESTONE_ICON_SIZE) / 2),
            MILESTONE_ICON_SIZE, MILESTONE_ICON_SIZE, 1,
            labelColor[1], labelColor[2], labelColor[3])
    end
    self:drawText(commaValue(data.threshold), 30, textY,
        labelColor[1], labelColor[2], labelColor[3], 1, UIFont.Small)
    local statusLeft = milestoneRight(contentWidth)
    local progressX = progressLeft(contentWidth)
    self:drawTextCentre(status, statusLeft + math.floor((progressX - statusLeft) / 2),
        textY, r, g, b, 1, UIFont.Small)

    local padding = Layout.columnPadding()
    local barHeight = Layout.progressBarHeight()
    local barX, barY, barWidth = progressX + padding,
        y + math.floor((self.itemheight - barHeight) / 2),
        contentWidth - progressX - padding * 2
    self:drawRect(barX, barY, barWidth, barHeight, 0.82, 0.02, 0.02, 0.02)
    if data.progress > 0 then
        local fillR, fillG, fillB = 0.18, 0.58, 0.12
        if data.active then fillR, fillG, fillB = 0.58, 0.42, 0.08 end
        self:drawRect(barX + 1, barY + 1, math.floor((barWidth - 2) * data.progress),
            barHeight - 2, 0.76, fillR, fillG, fillB)
    end
    self:drawRectBorder(barX, barY, barWidth, barHeight, 0.55, 0.5, 0.5, 0.5)

    local barText
    if data.reached then
        barText = "100%"
    elseif data.active then
        local current = math.max(0, math.min(data.current, data.threshold))
        barText = commaValue(current) .. " / " .. commaValue(data.threshold) ..
            " (" .. percentValue(data.progress) .. "%)"
    else
        barText = L.text("UI_TGSRR_Tracker_MilestoneLocked", "Locked")
    end
    self:drawTextCentre(barText, barX + barWidth / 2, textY,
        labelColor[1], labelColor[2], labelColor[3], 1, UIFont.Small)
    return y + self.itemheight
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
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    o.playerAvailable = false
    o.current = 0
    o.percent = 0
    return o
end

return View
