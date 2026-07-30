require "ISUI/ISPanel"

local View = ISPanel:derive("TGSRRPendingTrackerView")

function View:prerender()
    ISPanel.prerender(self)
    local x, y = 16, 16
    self:drawText(self.heading, x, y, 1, 1, 1, 1, UIFont.Medium)
    y = y + getTextManager():getFontHeight(UIFont.Medium) + 12
    self:drawText(self.message, x, y, 0.72, 0.72, 0.72, 1, UIFont.Small)
end

function View:onShow() self:setVisible(true) end
function View:onHide() self:setVisible(false) end

function View:onResize(width, height)
    self:setWidth(width)
    self:setHeight(height)
end

function View:new(x, y, width, height, heading, message)
    local o = ISPanel.new(self, x, y, width, height)
    o.background = false
    o.heading = heading
    o.message = message
    return o
end

return View
