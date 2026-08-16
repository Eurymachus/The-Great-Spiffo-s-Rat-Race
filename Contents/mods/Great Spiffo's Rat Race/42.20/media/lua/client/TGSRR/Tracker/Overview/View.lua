require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Deliverables = require "TGSRR/Challenge/Deliverables"
local L = require "TGSRR/Core/Localization"
local Notifications = require "TGSRR/Challenge/Notifications"
local ProgressWeights = require "TGSRR/Challenge/ProgressWeights"
local Layout = require "TGSRR/Tracker/Layout"

local View = ISPanel:derive("TGSRROverviewTrackerView")
local REFRESH_INTERVAL_MS = 1000
local CONTENT_MARGIN = 8
local function footerHeight() return Layout.boxHeight(UIFont.Small, 5, 22) end
local function cardHeight()
    return math.max(104,
        12 + math.max(Layout.lineHeight(UIFont.Medium), Layout.lineHeight(UIFont.Small))
            + 8 + 18 + 5 + Layout.lineHeight(UIFont.Small) + 12)
end

local function commaValue(value)
    local text = tostring(math.max(0, math.floor(tonumber(value) or 0)))
    while true do
        local replaced
        text, replaced = text:gsub("^(-?%d+)(%d%d%d)", "%1,%2")
        if replaced == 0 then return text end
    end
end

local function formatCount(record)
    if record.current == nil or record.target == nil then
        if record.target ~= nil then return "- / " .. tostring(record.target) end
        return L.text("UI_TGSRR_Tracker_NotTracked", "Not tracked")
    end
    return commaValue(record.current) .. " / " .. commaValue(record.target)
end

local function formatPercent(value)
    value = math.max(0, tonumber(value) or 0)
    if value == 0 then return "0%" end
    local decimals = 1
    if value < 0.001 then
        decimals = 4
    elseif value < 0.01 then
        decimals = 3
    elseif value < 0.1 then
        decimals = 2
    end
    local text = string.format("%." .. tostring(decimals) .. "f", value)
    text = text:gsub("0+$", ""):gsub("%.$", "")
    return text .. "%"
end

function View:createChildren()
    ISPanel.createChildren(self)
    self.list = ISScrollingListBox:new(CONTENT_MARGIN, CONTENT_MARGIN,
        self.width - CONTENT_MARGIN * 2,
        self.height - CONTENT_MARGIN * 3 - footerHeight())
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = cardHeight()
    self.list.doDrawItem = self.drawDeliverable
    self.list.drawBorder = false
    self.list:setOnMouseDoubleClick(self, View.onActivate)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:prerender()
    ISPanel.prerender(self)
    local x = CONTENT_MARGIN
    local footer = footerHeight()
    local y = self.height - CONTENT_MARGIN - footer
    local width = self.width - CONTENT_MARGIN * 2
    local percent = self.overallPercent or 0
    self:drawRect(x, y, width, footer, 0.8, 0.02, 0.02, 0.02)
    if percent > 0 then
        self:drawRect(x + 1, y + 1,
            math.floor((width - 2) * percent / 100), footer - 2,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(x, y, width, footer,
        0.62, 0.55, 0.55, 0.55)
    local textY = y + math.floor((footer - Layout.lineHeight(UIFont.Small)) / 2)
    self:drawTextCentre(
        L.text("UI_TGSRR_Tracker_OverallProgress", "Overall progress")
            .. ": " .. formatPercent(percent),
        x + width / 2, textY, 1, 1, 1, 1, UIFont.Small)
end

function View:drawDeliverable(y, item, alt)
    local record = item.item
    local scrollWidth = self:isVScrollBarVisible() and self.vscroll:getWidth() or 0
    local width = self:getWidth() - scrollWidth
    local hovered = self.mouseoverselected == item.index
    local available = record.available ~= false

    self:drawRect(0, y + 4, width, self.itemheight - 8,
        hovered and 0.82 or 0.68, 0.045, 0.045, 0.045)
    self:drawRectBorder(0, y + 4, width, self.itemheight - 8,
        hovered and 0.85 or 0.55, 0.62, 0.62, 0.62)

    local titleY = y + 12
    local titleColor = available and 1 or 0.62
    self:drawText(record.label, 12, titleY,
        titleColor, titleColor, titleColor, 1, UIFont.Medium)

    local count = formatCount(record)
    self:drawTextRight(count, width - 12, titleY,
        titleColor, titleColor, titleColor, 1, UIFont.Small)

    local barX = 12
    local barY = titleY + math.max(Layout.lineHeight(UIFont.Medium),
        Layout.lineHeight(UIFont.Small)) + 8
    local barWidth = width - 24
    self:drawRect(barX, barY, barWidth, 18, 0.8, 0.02, 0.02, 0.02)
    if available and record.percent > 0 then
        self:drawRect(barX + 1, barY + 1,
            math.floor((barWidth - 2) * record.percent / 100), 16,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(barX, barY, barWidth, 18, 0.62, 0.55, 0.55, 0.55)

    local percentText = available and formatPercent(record.percent) or
        L.text("UI_TGSRR_Tracker_Unavailable", "Unavailable")
    local detailY = barY + 18 + 5
    self:drawTextRight(percentText, width - 12, detailY,
        titleColor, titleColor, titleColor, 1, UIFont.Small)
    self:drawText(record.detail or "", 12, detailY,
        0.7, 0.7, 0.7, 1, UIFont.Small)
    return y + self.itemheight
end

function View:refresh(player)
    if not self.list then return end
    local records = Deliverables.getAll({ player = player })
    self.overallPercent = ProgressWeights.calculate(records)
    local rebuild = #self.list.items ~= #records
    if not rebuild then
        for index, record in ipairs(records) do
            if self.list.items[index].item.id ~= record.id then rebuild = true; break end
        end
    end

    if rebuild then
        self.list:clear()
        for _, record in ipairs(records) do self.list:addItem(record.label, record) end
    else
        for index, record in ipairs(records) do
            self.list.items[index].text = record.label
            self.list.items[index].item = record
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

function View:onActivate(record)
    if not record or not record.detailTab then return end
    if self.parent and self.parent.selectTab then self.parent:selectTab(record.detailTab) end
end

function View:onShow()
    self:setVisible(true)
    local player = getSpecificPlayer(0) or getPlayer()
    Deliverables.refreshAll({ player = player })
    self:refresh(player)
end

function View:onHide() self:setVisible(false) end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
    if self.list then
        self.list:setWidth(width - CONTENT_MARGIN * 2)
        self.list.itemheight = cardHeight()
        self.list:setHeight(height - CONTENT_MARGIN * 3 - footerHeight())
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    View.instance = o
    return o
end

Notifications.subscribe("overview-tracker-view", function()
    local view = View.instance
    if view and view:getIsVisible() then view:refresh(getSpecificPlayer(0) or getPlayer()) end
end)

return View
