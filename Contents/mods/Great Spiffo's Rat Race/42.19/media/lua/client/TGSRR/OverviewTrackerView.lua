require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Deliverables = require "TGSRR/ChallengeDeliverables"
local L = require "TGSRR/Localization"

local View = ISPanel:derive("TGSRROverviewTrackerView")
local REFRESH_INTERVAL_MS = 1000
local CONTENT_MARGIN = 8
local CARD_HEIGHT = 104

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

function View:createChildren()
    ISPanel.createChildren(self)
    self.list = ISScrollingListBox:new(CONTENT_MARGIN, CONTENT_MARGIN,
        self.width - CONTENT_MARGIN * 2, self.height - CONTENT_MARGIN * 2)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = CARD_HEIGHT
    self.list.doDrawItem = self.drawDeliverable
    self.list.drawBorder = false
    self.list:setOnMouseDoubleClick(self, View.onActivate)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
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
    local barY = y + 43
    local barWidth = width - 24
    self:drawRect(barX, barY, barWidth, 18, 0.8, 0.02, 0.02, 0.02)
    if available and record.percent > 0 then
        self:drawRect(barX + 1, barY + 1,
            math.floor((barWidth - 2) * record.percent / 100), 16,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(barX, barY, barWidth, 18, 0.62, 0.55, 0.55, 0.55)

    local percentText = available and string.format("%.1f%%", record.percent) or
        L.text("UI_TGSRR_Tracker_Unavailable", "Unavailable")
    self:drawTextRight(percentText, width - 12, y + 66,
        titleColor, titleColor, titleColor, 1, UIFont.Small)
    self:drawText(record.detail or "", 12, y + 66,
        0.7, 0.7, 0.7, 1, UIFont.Small)
    return y + self.itemheight
end

function View:refresh(player)
    if not self.list then return end
    local records = Deliverables.getAll({ player = player })
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
        self.list:setHeight(height - CONTENT_MARGIN * 2)
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    return o
end

return View
