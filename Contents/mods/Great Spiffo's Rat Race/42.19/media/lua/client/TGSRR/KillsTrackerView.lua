require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local KillsData = require "TGSRR/KillsTrackerData"
local L = require "TGSRR/Localization"

local View = ISPanel:derive("TGSRRKillsTrackerView")
local TARGET_KILLS = 1000000
local MARGIN = 8
local GOAL_BAR_Y = 8
local GOAL_BAR_HEIGHT = 22
local HEADER_Y = 38
local HEADER_HEIGHT = 28
local LIST_TOP = HEADER_Y + HEADER_HEIGHT
local ROW_HEIGHT = 27
local COLUMN_RATIOS = { 0.44, 0.70 }

local function columnX(width, index)
    return math.floor(width * COLUMN_RATIOS[index])
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
    if percent >= 1 then return string.format("%.1f", percent):gsub("%.0$", "") end
    if percent >= 0.1 then return string.format("%.1f", percent) end
    return string.format("%.2f", percent):gsub("0+$", ""):gsub("%.$", "")
end

function View:createChildren()
    ISPanel.createChildren(self)
    self.list = ISScrollingListBox:new(MARGIN, LIST_TOP, self.width - MARGIN * 2,
        self.height - LIST_TOP - MARGIN)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = ROW_HEIGHT
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

    local scrollWidth = self.list and self.list:isVScrollBarVisible() and self.list.vscroll:getWidth() or 0
    local width = self.width - MARGIN * 2 - scrollWidth
    self:drawRect(MARGIN, GOAL_BAR_Y, width, GOAL_BAR_HEIGHT, 0.8, 0.02, 0.02, 0.02)
    if self.percent > 0 then
        self:drawRect(MARGIN + 1, GOAL_BAR_Y + 1, math.floor((width - 2) * self.percent / 100),
            GOAL_BAR_HEIGHT - 2, 0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(MARGIN, GOAL_BAR_Y, width, GOAL_BAR_HEIGHT, 0.62, 0.55, 0.55, 0.55)
    local textY = GOAL_BAR_Y + math.floor((GOAL_BAR_HEIGHT - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local progressText = self.playerAvailable and
        (commaValue(self.current) .. " " .. L.text("UI_TGSRR_Tracker_Of", "of") .. " " .. commaValue(TARGET_KILLS)) or
        L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable.")
    self:drawTextCentre(progressText, MARGIN + width / 2, textY, 1, 1, 1, 1, UIFont.Small)

    self:drawRect(MARGIN, HEADER_Y, width, HEADER_HEIGHT, 0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(MARGIN, HEADER_Y, width, HEADER_HEIGHT, 0.7, 0.65, 0.65, 0.65)
    local headerTextY = HEADER_Y + math.floor((HEADER_HEIGHT - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawText(L.text("UI_TGSRR_Tracker_Milestone", "Milestone"),
        MARGIN + 8, headerTextY, 1, 1, 1, 1, UIFont.Small)
    local headers = {
        L.text("UI_TGSRR_Tracker_Status", "Status"),
        L.text("UI_TGSRR_Tracker_Progress", "Progress"),
    }
    local left = columnX(width, 1)
    for index, header in ipairs(headers) do
        local right = index < #headers and columnX(width, index + 1) or width
        self:drawTextCentre(header, MARGIN + left + math.floor((right - left) / 2), headerTextY,
            1, 1, 1, 1, UIFont.Small)
        left = right
    end
end

function View:drawMilestone(y, item, alt)
    local data = item.item
    local width = self:getWidth() - (self:isVScrollBarVisible() and self.vscroll:getWidth() or 0)
    if item.index % 2 == 0 then self:drawRect(0, y, width, self.itemheight - 1, 0.18, 0.12, 0.12, 0.12) end
    self:drawRect(0, y + self.itemheight - 1, width, 1, 0.3, 0.5, 0.5, 0.5)

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
    self:drawText(commaValue(data.threshold), 8, textY, r, g, b, 1, UIFont.Small)
    local statusLeft = columnX(width, 1)
    local progressLeft = columnX(width, 2)
    self:drawTextCentre(status, statusLeft + math.floor((progressLeft - statusLeft) / 2),
        textY, r, g, b, 1, UIFont.Small)

    local barX, barY, barWidth, barHeight = progressLeft + 6,
        y + math.floor((self.itemheight - 17) / 2), width - progressLeft - 12, 17
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
    self:drawTextCentre(barText, barX + barWidth / 2, textY, 0.9, 0.9, 0.9, 1, UIFont.Small)
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
        self.list:setHeight(height - LIST_TOP - MARGIN)
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
