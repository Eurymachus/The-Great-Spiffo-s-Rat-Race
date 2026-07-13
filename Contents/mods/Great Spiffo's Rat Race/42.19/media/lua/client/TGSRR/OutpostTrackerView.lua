require "ISUI/ISPanel"
require "ISUI/ISScrollingListBox"

local Outposts = require "TGSRR/OutpostDefinitions"
require "TGSRR/OutpostRoomActivationCheck"

local View = ISPanel:derive("TGSRROutpostTrackerView")
local REFRESH_INTERVAL_MS = 1000

local function activationResult(outpost, player)
    local inspection = Outposts.inspect(outpost, { player = player })
    return inspection.checks and inspection.checks.room_activation or nil
end

function View:createChildren()
    ISPanel.createChildren(self)
    self.list = ISScrollingListBox:new(8, 8, self.width - 16, self.height - 16)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = 36
    self.list.vscroll:setVisible(true)
    self.list.doDrawItem = self.drawOutpost
    self.list:setOnMouseDoubleClick(self, View.onActivate)
    self:addChild(self.list)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:drawOutpost(y, item, alt)
    local data = item.item
    local barX, barY = 8, y + 4
    local barW, barH = self:getWidth() - 30, self.itemheight - 8
    local hovered = self.mouseoverselected == item.index
    self:drawRect(barX, barY, barW, barH, hovered and 0.92 or 0.78, 0.035, 0.035, 0.035)
    if data.progress > 0 then
        self:drawRect(barX + 1, barY + 1, math.floor((barW - 2) * data.progress), barH - 2,
            hovered and 0.78 or 0.64, data.r, data.g, data.b)
    end
    self:drawRectBorder(barX, barY, barW, barH, 0.95, 0.82, 0.82, 0.82)
    local textY = barY + math.floor((barH - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawText(data.title, barX + 8, textY, 1, 1, 1, 1, UIFont.Small)
    self:drawTextRight(data.progressText, barX + barW - 8, textY, 1, 1, 1, 1, UIFont.Small)
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
    local selectedId = self.list.items[self.list.selected] and self.list.items[self.list.selected].item.id or nil
    local scrollY = self.list:getYScroll()
    self.list:clear()
    for _, outpost in ipairs(Outposts.getAll()) do
        local activation = activationResult(outpost, player)
        local current = activation and activation.activatedRooms or 0
        local required = activation and activation.totalRooms or 0
        local complete = required > 0 and current >= required
        local progress = required > 0 and current / required or 0
        local percent = math.floor(progress * 100 + 0.5)
        local data = {
            id = outpost.id,
            title = outpost.name,
            progressText = tostring(percent) .. "/100%",
            progress = math.max(0, math.min(1, progress)),
            r = 0.12,
            g = complete and 0.72 or 0.52,
            b = 0.18,
            outpost = outpost,
            activation = activation,
        }
        local item = self.list:addItem(outpost.name, data, buildTooltip(outpost, activation, percent))
        if selectedId == outpost.id then self.list.selected = item.itemindex end
    end
    self.list:setYScroll(scrollY)
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
        self.list:setHeight(height - 16)
        self.list.vscroll:setVisible(true)
        self.list.vscroll:bringToTop()
    end
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    return o
end

return View
