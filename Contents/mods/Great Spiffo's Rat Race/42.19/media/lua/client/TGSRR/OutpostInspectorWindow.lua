require "ISUI/ISCollapsableWindow"
require "ISUI/ISScrollingListBox"
require "ISUI/ISButton"

local Outposts = require "TGSRR/OutpostDefinitions"
require "TGSRR/OutpostRoomActivationCheck"

local Inspector = ISCollapsableWindow:derive("TGSRROutpostInspectorWindow")
Inspector.instance = nil
local STATE_FILE = "TGSRR/OutpostInspectorWindow.ini"

local function loadWindowState()
    local reader = getFileReader(STATE_FILE, false)
    if not reader then return nil end
    local state = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local key, value = line:match("^%s*(.-)%s*=%s*(.-)%s*$")
        if key then state[key] = tonumber(value) end
    end
    reader:close()
    if not state.x or not state.y or not state.width or not state.height then return nil end
    return state
end

local function saveWindowState(window)
    local writer = getFileWriter(STATE_FILE, true, false)
    if not writer then return end
    writer:write("[Window]\n")
    writer:write("x=" .. tostring(math.floor(window:getX())) .. "\n")
    writer:write("y=" .. tostring(math.floor(window:getY())) .. "\n")
    writer:write("width=" .. tostring(math.floor(window:getWidth())) .. "\n")
    writer:write("height=" .. tostring(math.floor(window:getHeight())) .. "\n")
    writer:close()
end

local function addLine(lines, text, state, data)
    lines[#lines + 1] = { text = text, state = state or "neutral", data = data }
end

local function buildLines(result)
    local lines = {}
    local activation = result.checks.room_activation
    if not activation then
        addLine(lines, "Room activation check is not registered.", "fail")
        return lines
    end

    addLine(lines, "Buildings: " .. tostring(activation.resolvedBuildings) .. " / " .. tostring(activation.expectedBuildings),
        #activation.missingBuildings == 0 and "pass" or "fail")
    for _, id in ipairs(activation.missingBuildings) do
        addLine(lines, "  Missing BuildingDef: " .. id, "fail")
    end
    addLine(lines, "Rooms activated: " .. tostring(activation.activatedRooms) .. " / " .. tostring(activation.totalRooms),
        activation.activatedRooms == activation.totalRooms and activation.totalRooms > 0 and "pass" or "partial")
    addLine(lines, "Rooms with loaded squares: " .. tostring(activation.loadedRooms) .. " / " .. tostring(activation.totalRooms),
        activation.loadedRooms > 0 and "neutral" or "partial")
    addLine(lines, "Floors activated: " .. tostring(activation.activatedFloors) .. " / " .. tostring(activation.totalFloors),
        activation.activatedFloors == activation.totalFloors and activation.totalFloors > 0 and "pass" or "partial")
    addLine(lines, "", "neutral")

    for _, floor in ipairs(activation.floors) do
        local state = floor.passed and "pass" or (floor.activated > 0 and "partial" or "fail")
        addLine(lines, string.format("Level %d: %d / %d activated, %d loaded",
            floor.level, floor.activated, floor.total, floor.loaded), state, floor)
        if not floor.passed then
            for _, room in ipairs(floor.inactiveRooms) do
                addLine(lines, "    " .. room.name .. "  [" .. room.id .. "]", "fail", room)
            end
        end
    end
    return lines
end

function Inspector:createChildren()
    ISCollapsableWindow.createChildren(self)
    local top = self:titleBarHeight() + 6
    local footer = self:resizeWidgetHeight()
    self.list = ISScrollingListBox:new(8, top, self.width - 16, self.height - top - footer - 42)
    self.list:initialise()
    self.list.itemheight = getTextManager():getFontHeight(UIFont.Small) + 6
    self.list.doDrawItem = self.drawItem
    self.list.anchorLeft = true
    self.list.anchorRight = true
    self.list.anchorTop = true
    self.list.anchorBottom = true
    self:addChild(self.list)

    self.refreshButton = ISButton:new(8, self.height - footer - 34, self.width - 16, 26,
        "Refresh Inspection", self, self.onRefresh)
    self.refreshButton:initialise()
    self.refreshButton.anchorLeft = true
    self.refreshButton.anchorRight = true
    self.refreshButton.anchorTop = false
    self.refreshButton.anchorBottom = true
    self:addChild(self.refreshButton)
    self:setResult(self.result)
end

function Inspector:onRefresh()
    if not self.outpost then return end
    self:setResult(Outposts.inspect(self.outpost, { player = getSpecificPlayer(0) or getPlayer() }))
end

function Inspector:onResize()
    ISUIElement.onResize(self)
    if not self.list then return end
    local top = self:titleBarHeight() + 6
    local footer = self:resizeWidgetHeight()
    self.list:setX(8)
    self.list:setY(top)
    self.list:setWidth(self.width - 16)
    self.list:setHeight(self.height - top - footer - 42)
    if self.refreshButton then
        self.refreshButton:setX(8)
        self.refreshButton:setY(self.height - footer - 34)
        self.refreshButton:setWidth(self.width - 16)
    end
    saveWindowState(self)
end

function Inspector:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    saveWindowState(self)
end

function Inspector:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    saveWindowState(self)
end

function Inspector:close()
    saveWindowState(self)
    ISCollapsableWindow.close(self)
end

function Inspector:drawItem(y, item, alt)
    local colors = {
        pass = { 0.35, 1.0, 0.35 },
        partial = { 1.0, 0.75, 0.2 },
        fail = { 1.0, 0.3, 0.3 },
        neutral = { 0.9, 0.9, 0.9 },
    }
    local color = colors[item.item.state] or colors.neutral
    self:drawText(item.text, 6, y + 3, color[1], color[2], color[3], 1, UIFont.Small)
    return y + self.itemheight
end

function Inspector:setResult(result)
    self.result = result
    self.title = "TGSRR Inspector - " .. tostring(result and result.name or "Unknown")
    if not self.list then return end
    self.list:clear()
    for _, line in ipairs(buildLines(result or { checks = {} })) do
        self.list:addItem(line.text, line)
    end
end

function Inspector:new(x, y, width, height, result)
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.result = result
    o.title = "TGSRR Outpost Inspector"
    o.resizable = true
    o.minimumWidth = 500
    o.minimumHeight = 300
    return o
end

function Inspector.showFor(outpost)
    local result = Outposts.inspect(outpost, { player = getSpecificPlayer(0) or getPlayer() })
    local window = Inspector.instance
    if not window then
        local state = loadWindowState()
        local width = state and math.max(500, state.width) or 620
        local height = state and math.max(300, state.height) or 520
        width = math.min(width, getCore():getScreenWidth())
        height = math.min(height, getCore():getScreenHeight())
        local x = state and state.x or math.floor((getCore():getScreenWidth() - width) / 2)
        local y = state and state.y or math.floor((getCore():getScreenHeight() - height) / 2)
        x = math.max(0, math.min(x, getCore():getScreenWidth() - width))
        y = math.max(0, math.min(y, getCore():getScreenHeight() - height))
        window = Inspector:new(x, y, width, height, result)
        window.outpost = outpost
        window:initialise()
        Inspector.instance = window
    else
        window.outpost = outpost
        window:setResult(result)
    end
    window:addToUIManager()
    window:setVisible(true)
    window:bringToTop()
    return result
end

return Inspector
