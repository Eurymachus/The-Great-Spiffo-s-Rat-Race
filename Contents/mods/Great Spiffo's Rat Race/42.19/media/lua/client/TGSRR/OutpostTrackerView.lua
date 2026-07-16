require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Snapshot = require "TGSRR/OutpostTrackerSnapshot"

local View = ISPanel:derive("TGSRROutpostTrackerView")
local REFRESH_INTERVAL_MS = 1000
local HEADER_Y = 8
local HEADER_HEIGHT = 28
local LIST_BOTTOM_MARGIN = 8
local COLUMN_RATIOS = { 0.48, 0.62, 0.75, 0.90 }

local function columnX(width, index)
    return math.floor(width * COLUMN_RATIOS[index])
end

function View:createChildren()
    ISPanel.createChildren(self)
    local listY = HEADER_Y + HEADER_HEIGHT
    self.list = ISScrollingListBox:new(8, listY, self.width - 16, self.height - listY - LIST_BOTTOM_MARGIN)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = 27
    self.list.doDrawItem = self.drawOutpost
    self.list.drawBorder = true
    self.list:setOnMouseDoubleClick(self, View.onActivate)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:prerender()
    ISPanel.prerender(self)
    local x = 8
    local scrollWidth = self.list and self.list:isVScrollBarVisible() and self.list.vscroll:getWidth() or 0
    local width = self.width - 16 - scrollWidth
    self:drawRect(x, HEADER_Y, width, HEADER_HEIGHT, 0.9, 0.12, 0.12, 0.12)
    self:drawRectBorder(x, HEADER_Y, width, HEADER_HEIGHT, 0.7, 0.65, 0.65, 0.65)

    local textY = HEADER_Y + math.floor((HEADER_HEIGHT - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawText("Outpost", x + 8, textY, 1, 1, 1, 1, UIFont.Small)
    local headers = { "Rooms", "Floors", "Buildings", "%" }
    local left = columnX(width, 1)
    for index, header in ipairs(headers) do
        local right = index < #headers and columnX(width, index + 1) or width
        self:drawTextCentre(header, x + left + math.floor((right - left) / 2), textY,
            1, 1, 1, 1, UIFont.Small)
        left = right
    end
end

function View:drawOutpost(y, item, alt)
    local data = item.item
    local scrollWidth = self:isVScrollBarVisible() and self.vscroll:getWidth() or 0
    local width = self:getWidth() - scrollWidth
    local hovered = self.mouseoverselected == item.index
    if item.index % 2 == 0 then self:drawRect(0, y, width, self.itemheight - 1, 0.18, 0.12, 0.12, 0.12) end
    if hovered then self:drawRect(0, y, width, self.itemheight - 1, 0.4, 0.28, 0.28, 0.28) end
    self:drawRect(0, y + self.itemheight - 1, width, 1, 0.35, 0.6, 0.6, 0.6)

    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    local color = data.complete and { 0.42, 0.9, 0.48 } or { 1, 1, 1 }
    self:drawText(data.title, 8, textY, color[1], color[2], color[3], 1, UIFont.Small)
    local values = { data.rooms, data.floors, data.buildings, tostring(data.percent) .. "%" }
    local left = columnX(width, 1)
    for index, value in ipairs(values) do
        local right = index < #values and columnX(width, index + 1) or width
        self:drawTextCentre(value, left + math.floor((right - left) / 2), textY,
            color[1], color[2], color[3], 1, UIFont.Small)
        left = right
    end
    return y + self.itemheight
end

local function buildTooltip(outpost, activation, percent)
    local lines = {
        outpost.name,
        "Completion: " .. tostring(percent) .. "%",
    }
    if activation then
        lines[#lines + 1] = "Rooms activated: " .. activation.activatedRooms .. " / " .. activation.totalRooms
        lines[#lines + 1] = "Floors activated: " .. activation.activatedFloors .. " / " .. activation.totalFloors
        lines[#lines + 1] = "Buildings found: " .. activation.resolvedBuildings .. " / " .. activation.expectedBuildings
        if activation.loadedRooms ~= nil then
            lines[#lines + 1] = "Rooms currently loaded: " .. activation.loadedRooms .. " / " .. activation.totalRooms
        end
    else
        lines[#lines + 1] = "Outpost data has not been evaluated."
    end
    lines[#lines + 1] = "Double-click for details"
    return table.concat(lines, "\n")
end

function View:refresh(player)
    if not self.list then return end
    local snapshot = Snapshot.getAll(player)
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
                buildTooltip(row.outpost, row.activation, row.percent))
            if selectedId == row.id then self.list.selected = item.itemindex end
        end
        self.list:setYScroll(scrollY)
    else
        for index, row in ipairs(snapshot.rows) do
            local item = self.list.items[index]
            item.text = row.title
            item.item = row
            item.tooltip = buildTooltip(row.outpost, row.activation, row.percent)
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
    local Inspector = require "TGSRR/OutpostInspectorWindow"
    Inspector.showFor(item.outpost)
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
        self.list:setWidth(width - 16)
        self.list:setHeight(height - HEADER_Y - HEADER_HEIGHT - LIST_BOTTOM_MARGIN)
        self.list.vscroll:bringToTop()
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    return o
end

return View
