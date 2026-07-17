require "ISUI/ISPanel"

local KillsData = require "TGSRR/KillsTrackerData"
local L = require "TGSRR/Localization"

local View = ISPanel:derive("TGSRRKillsTrackerView")
local TARGET_KILLS = 1000000

local function commaValue(value)
    local text = tostring(math.max(0, math.floor(tonumber(value) or 0)))
    while true do
        local replaced
        text, replaced = text:gsub("^(-?%d+)(%d%d%d)", "%1,%2")
        if replaced == 0 then return text end
    end
end

function View:refresh(player)
    local record = KillsData.refresh(player)
    self.playerAvailable = record.available
    self.current = record.current or 0
    self.remaining = math.max(0, TARGET_KILLS - self.current)
    self.percent = record.percent
end

function View:prerender()
    ISPanel.prerender(self)
    local record = KillsData.getRecord()
    self.playerAvailable = record.available
    self.current = record.current or 0
    self.remaining = math.max(0, TARGET_KILLS - self.current)
    self.percent = record.percent
    local margin = 24
    local width = self.width - margin * 2
    local y = 24

    self:drawText(L.text("UI_TGSRR_Tracker_ZombieKills", "Zombie Kills"), margin, y,
        1, 1, 1, 1, UIFont.Large)
    y = y + getTextManager():getFontHeight(UIFont.Large) + 18

    if not self.playerAvailable then
        self:drawText(L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable."),
            margin, y, 0.75, 0.75, 0.75, 1, UIFont.Small)
        return
    end

    self:drawText(commaValue(self.current), margin, y, 1, 1, 1, 1, UIFont.Large)
    self:drawTextRight(L.text("UI_TGSRR_Tracker_Of", "of") .. " " .. commaValue(TARGET_KILLS), margin + width, y,
        0.75, 0.75, 0.75, 1, UIFont.Medium)
    y = y + getTextManager():getFontHeight(UIFont.Large) + 18

    local barHeight = 30
    self:drawRect(margin, y, width, barHeight, 0.82, 0.02, 0.02, 0.02)
    if self.percent > 0 then
        self:drawRect(margin + 1, y + 1, math.floor((width - 2) * self.percent / 100),
            barHeight - 2, 0.78, 0.58, 0.12, 0.12)
    end
    self:drawRectBorder(margin, y, width, barHeight, 0.75, 0.65, 0.65, 0.65)
    self:drawTextCentre(string.format("%.3f%%", self.percent), margin + width / 2,
        y + math.floor((barHeight - getTextManager():getFontHeight(UIFont.Small)) / 2),
        1, 1, 1, 1, UIFont.Small)
    y = y + barHeight + 20

    self:drawText(L.text("UI_TGSRR_Tracker_Remaining", "Remaining"),
        margin, y, 0.72, 0.72, 0.72, 1, UIFont.Small)
    self:drawTextRight(commaValue(self.remaining), margin + width, y, 1, 1, 1, 1, UIFont.Small)
end

function View:onShow()
    self:setVisible(true)
    self:refresh(getSpecificPlayer(0) or getPlayer())
end

function View:onHide() self:setVisible(false) end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
end

function View:new(x, y, width, height)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    o.playerAvailable = false
    o.current = 0
    o.remaining = TARGET_KILLS
    o.percent = 0
    return o
end

return View
