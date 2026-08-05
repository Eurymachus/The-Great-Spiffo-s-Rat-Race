require "ISUI/ISButton"
require "ISUI/ISCollapsableWindow"

local Palette = {}
local Panel = ISCollapsableWindow:derive("TGSRRDebugLauncherPalette")

local STATE_FILE = "TGSRR/DebugLauncherPalette.ini"
local BUTTON_WIDTH = 166
local BUTTON_HEIGHT = 26
local PADDING = 8
local TITLE_HEIGHT = 24

local entries = {}
local entriesById = {}
local panelInstance = nil

local function loadPosition(defaultX, defaultY)
    local reader = getFileReader(STATE_FILE, false)
    if not reader then return defaultX, defaultY end
    local x, y = nil, nil
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local key, value = line:match("^%s*(.-)%s*=%s*(.-)%s*$")
        if key == "x" then x = tonumber(value) end
        if key == "y" then y = tonumber(value) end
    end
    reader:close()
    return x or defaultX, y or defaultY
end

local function savePosition(panel)
    local writer = getFileWriter(STATE_FILE, true, false)
    if not writer then return end
    writer:write("[Window]\n")
    writer:write("x=" .. tostring(math.floor(panel:getX())) .. "\n")
    writer:write("y=" .. tostring(math.floor(panel:getY())) .. "\n")
    writer:close()
end

local function sortEntries()
    table.sort(entries, function(a, b)
        if a.order == b.order then return a.id < b.id end
        return a.order < b.order
    end)
end

local function invoke(entry)
    if entry and entry.callback then entry.callback() end
end

function Panel:addEntryButton(entry, index)
    local button = ISButton:new(
        PADDING, TITLE_HEIGHT + PADDING + (index - 1) * (BUTTON_HEIGHT + 4),
        BUTTON_WIDTH, BUTTON_HEIGHT, entry.label, entry, invoke)
    button:initialise()
    button:instantiate()
    self:addChild(button)
    self.entryButtons[#self.entryButtons + 1] = button
end

function Panel:rebuildButtons()
    for _, button in ipairs(self.entryButtons or {}) do
        self:removeChild(button)
    end
    self.entryButtons = {}
    for index, entry in ipairs(entries) do
        self:addEntryButton(entry, index)
    end
    self:setHeight(TITLE_HEIGHT + PADDING * 2
        + #entries * BUTTON_HEIGHT + math.max(0, #entries - 1) * 4)
end

function Panel:createChildren()
    ISCollapsableWindow.createChildren(self)
    self.closeButton:setVisible(false)
    self.entryButtons = {}
    self:rebuildButtons()
end

function Panel:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    savePosition(self)
end

function Panel:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    savePosition(self)
end

function Panel:new(x, y)
    local height = TITLE_HEIGHT + PADDING * 2
        + #entries * BUTTON_HEIGHT + math.max(0, #entries - 1) * 4
    local panel = ISCollapsableWindow.new(
        self, x, y, BUTTON_WIDTH + PADDING * 2, height)
    panel.title = "TGSRR Debug"
    panel.resizable = false
    panel.pin = true
    panel.alwaysOnTop = true
    return panel
end

function Palette.register(id, label, callback, order)
    local existing = entriesById[id]
    if existing then
        existing.label = label
        existing.callback = callback
        existing.order = order or existing.order
        sortEntries()
        if panelInstance then panelInstance:rebuildButtons() end
        return
    end
    local entry = {
        id = tostring(id),
        label = tostring(label),
        callback = callback,
        order = tonumber(order) or 100,
    }
    entries[#entries + 1] = entry
    entriesById[entry.id] = entry
    sortEntries()
    if panelInstance then panelInstance:rebuildButtons() end
end

local function createPalette()
    if not isDebugEnabled() or panelInstance or #entries == 0 then return end
    local width = BUTTON_WIDTH + PADDING * 2
    local height = TITLE_HEIGHT + PADDING * 2
        + #entries * BUTTON_HEIGHT + math.max(0, #entries - 1) * 4
    local defaultX = math.max(10, getCore():getScreenWidth() - width - 12)
    local defaultY = math.max(10, getCore():getScreenHeight() - height - 12)
    local x, y = loadPosition(defaultX, defaultY)
    x = math.max(0, math.min(x, getCore():getScreenWidth() - width))
    y = math.max(0, math.min(y, getCore():getScreenHeight() - height))

    panelInstance = Panel:new(x, y)
    panelInstance:initialise()
    panelInstance:addToUIManager()
end

Events.OnGameStart.Add(createPalette)

return Palette
