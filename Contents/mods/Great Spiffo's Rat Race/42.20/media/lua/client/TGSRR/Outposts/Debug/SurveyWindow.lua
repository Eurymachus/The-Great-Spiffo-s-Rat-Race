require "ISUI/ISCollapsableWindow"
require "ISUI/ISButton"

local SurveyIO = require "TGSRR/Outposts/Debug/SurveyIO"
local ZoneEditor = require "TGSRR/Outposts/Debug/ZoneEditor"
local Outposts = require "TGSRR/Outposts/Definitions"
local Inspector = require "TGSRR/Outposts/Debug/InspectorWindow"
local LauncherPalette = require "TGSRR/Debug/LauncherPalette"

TGSRROutpostSurveyWindow = ISCollapsableWindow:derive("TGSRROutpostSurveyWindow")
TGSRROutpostSurveyWindow.instance = nil

local OUTPOSTS = {
    { id = "Louisville", name = "Louisville" },
    { id = "Irvington", name = "Irvington" },
    { id = "Brandenburg", name = "Brandenburg" },
    { id = "Muldraugh", name = "Muldraugh" },
    { id = "WestPoint", name = "West Point" },
    { id = "Rosewood", name = "Rosewood" },
    { id = "MarchRidge", name = "March Ridge" },
    { id = "Ekron", name = "Ekron" },
    { id = "Riverside", name = "Riverside" },
    { id = "ValleyStation", name = "Valley Station" },
    { id = "EchoCreek", name = "Echo Creek" },
    { id = "HogWallowMilitaryBase", name = "Hog Wallow Military Base" },
    { id = "FallasLake", name = "Fallas Lake" },
}

local KEY_ORDER = {
    "name", "gameVersion", "worldAgeHours",
    "playerX", "playerY", "playerZ", "roomName", "roomId",
    "buildingId", "buildingMinX", "buildingMinY", "buildingMaxX", "buildingMaxY",
    "buildingWidth", "buildingHeight", "buildingRoomCount", "roomNames",
    "buildingChunkX", "buildingChunkY", "playerChunkX", "playerChunkY",
    "clearanceCenterX", "clearanceCenterY", "clearanceMinX", "clearanceMinY",
    "clearanceMaxX", "clearanceMaxY", "clearanceWidth", "clearanceHeight",
    "zoneMinX", "zoneMinY", "zoneMaxX", "zoneMaxY", "zoneWidth", "zoneHeight",
    "zoneBuildingCount",
}

local function javaListToNames(rooms)
    local names = {}
    if not rooms then return "" end
    for index = 0, rooms:size() - 1 do
        local room = rooms:get(index)
        local name = room and room:getName() or nil
        names[#names + 1] = tostring(name or "<unnamed>") .. "@" .. tostring(room:getZ())
    end
    table.sort(names)
    return table.concat(names, ",")
end

local function copySavedZone(target, source)
    if not source then return end
    for key, value in pairs(source) do
        if tostring(key):match("^zone") then
            target[key] = value
        end
    end
end

local function captureOutpost(outpost, savedZone)
    local player = getSpecificPlayer(0) or getPlayer()
    if not player then return false, "No player is available." end
    if player:getVehicle() then return false, "Leave the vehicle and stand inside the outpost building." end

    local square = player:getCurrentSquare()
    if not square then return false, "The player's square is unavailable." end
    local room = square:getRoom()
    local building = square:getBuilding()
    if not room or not building then
        return false, "Stand inside a mapped room in the outpost building."
    end

    local def = building:getDef()
    local roomDef = room:getRoomDef()
    if not def or not roomDef then return false, "The building metadata is unavailable." end

    local x, y, z = square:getX(), square:getY(), square:getZ()
    -- The challenge clearance area is IsoCell-like: 150x150 tiles centred
    -- on the outpost, not a world grid aligned to multiples of 150.
    local centerX = math.floor((def:getX() + def:getX2() - 1) / 2)
    local centerY = math.floor((def:getY() + def:getY2() - 1) / 2)
    local minX, minY = centerX - 75, centerY - 75
    local row = {
        name = outpost.name,
        gameVersion = tostring(getCore():getVersionNumber()),
        worldAgeHours = getGameTime():getWorldAgeHours(),
        playerX = x, playerY = y, playerZ = z,
        roomName = tostring(room:getName() or "<unnamed>"),
        roomId = tostring(roomDef:getIDString()),
        buildingId = tostring(def:getIDString()),
        buildingMinX = def:getX(), buildingMinY = def:getY(),
        buildingMaxX = def:getX2() - 1, buildingMaxY = def:getY2() - 1,
        buildingWidth = def:getW(), buildingHeight = def:getH(),
        buildingRoomCount = def:getRoomsNumber(),
        roomNames = javaListToNames(def:getRooms()),
        buildingChunkX = def:getChunkX(), buildingChunkY = def:getChunkY(),
        playerChunkX = math.floor(x / 8), playerChunkY = math.floor(y / 8),
        clearanceCenterX = centerX, clearanceCenterY = centerY,
        clearanceMinX = minX, clearanceMinY = minY,
        clearanceMaxX = minX + 149, clearanceMaxY = minY + 149,
        clearanceWidth = 150, clearanceHeight = 150,
    }

    if savedZone then
        copySavedZone(row, savedZone)
        local refreshed, refreshError =
            ZoneEditor.refreshSavedZone(row)
        if not refreshed then return false, refreshError end
        if x < row.zoneMinX or x > row.zoneMaxX
                or y < row.zoneMinY or y > row.zoneMaxY then
            return false,
                "The current church anchor is outside the saved core zone. "
                    .. "Use New Survey instead."
        end
        if row.zoneMinX < row.clearanceMinX
                or row.zoneMinY < row.clearanceMinY
                or row.zoneMaxX > row.clearanceMaxX
                or row.zoneMaxY > row.clearanceMaxY then
            return false,
                "The saved core zone no longer fits the refreshed clearance "
                    .. "area. Use New Survey instead."
        end
    end

    if not SurveyIO.saveSection(outpost.id, row, KEY_ORDER) then
        return false, "Could not write " .. SurveyIO.getFilename() .. "."
    end
    return true,
        outpost.name .. " recorded at "
            .. x .. ", " .. y .. ", " .. z .. ".",
        row
end

function TGSRROutpostSurveyWindow:beginZoneEditor(outpost)
    local sections = SurveyIO.loadAll()
    local row = sections[outpost.id]
    if not row then return end
    self:setVisible(false)
    local editor = ZoneEditor:new(0, 0, 440, 180, getSpecificPlayer(0) or getPlayer(), self, outpost, row, KEY_ORDER)
    editor:initialise()
    editor:addToUIManager()
end

-- The vanilla designation-zone editor calls this on its parent when cancelled.
function TGSRROutpostSurveyWindow:populateList()
end

function TGSRROutpostSurveyWindow:createChildren()
    ISCollapsableWindow.createChildren(self)
    self.buttons = {}
    local captured = SurveyIO.loadAll()
    local definitionsByName = {}
    for _, definition in ipairs(Outposts.getAll()) do definitionsByName[definition.name] = definition end
    local y = self:titleBarHeight() + 10
    for _, outpost in ipairs(OUTPOSTS) do
        local teleportWidth = 48
        local inspectWidth = 30
        local button = ISButton:new(10, y, self.width - 26 - teleportWidth - inspectWidth, 24, outpost.name, self, self.onOutpostButton)
        button:initialise()
        button.outpost = outpost
        button.definition = definitionsByName[outpost.name]
        if captured[outpost.id] then
            button.backgroundColor = { r = 0.1, g = 0.45, b = 0.15, a = 1 }
        end
        self:addChild(button)
        self.buttons[outpost.id] = button

        local teleport = ISButton:new(button:getRight() + 3, y, teleportWidth, 24, "TP", self, self.onTeleportButton)
        teleport:initialise()
        teleport.outpost = outpost
        teleport.definition = definitionsByName[outpost.name]
        teleport.tooltip = "Teleport to the saved " .. outpost.name
            .. " survey anchor, or the registered anchor if no survey exists"
        self:addChild(teleport)

        local inspect = ISButton:new(teleport:getRight() + 3, y, inspectWidth, 24, "I", self, self.onInspectButton)
        inspect:initialise()
        inspect.definition = definitionsByName[outpost.name]
        inspect.outpost = outpost
        inspect.tooltip = "Inspect " .. outpost.name
        self:addChild(inspect)
        y = y + 27
    end
    self.inspectButton = ISButton:new(10, self.height - 32, self.width - 20, 24,
        "Inspect Nearest Outpost", self, self.onInspectNearest)
    self.inspectButton:initialise()
    self:addChild(self.inspectButton)
    self.status = "Select an outpost to review its saved survey."
end

function TGSRROutpostSurveyWindow:openInspector(outpost, definition)
    if not definition then
        self.status = "Inspection target is unavailable."
        return
    end
    local surveyRow = SurveyIO.loadAll()[outpost.id]
    Inspector.showFor(definition, {
        surveyRow = surveyRow,
        resurveyAction = function()
            self:resurveySavedArea(outpost, definition)
        end,
        newSurveyAction = function()
            self:newSurveyOutpost(outpost)
        end,
    })
    self.status = "Reviewing " .. definition.name
        .. (surveyRow and " saved survey." or " without a saved survey.")
end

function TGSRROutpostSurveyWindow:onInspectButton(button)
    self:openInspector(button.outpost, button.definition)
end

function TGSRROutpostSurveyWindow:onTeleportButton(button)
    local player = getSpecificPlayer(0) or getPlayer()
    local definition = button.definition
    if not player then
        self.status = "Teleport target is unavailable."
        return
    end

    local savedRow =
        button.outpost
        and SurveyIO.loadAll()[button.outpost.id]
        or nil
    local anchorX = tonumber(savedRow and savedRow.playerX)
    local anchorY = tonumber(savedRow and savedRow.playerY)
    local anchorZ = tonumber(savedRow and savedRow.playerZ)
    local source = "saved survey"

    if not anchorX or not anchorY or not anchorZ then
        local anchor = definition and definition.anchor or nil
        if not anchor then
            self.status = "Teleport target is unavailable."
            return
        end
        anchorX, anchorY, anchorZ =
            anchor.x, anchor.y, anchor.z
        source = "registered definition"
    end

    player:teleportTo(
        anchorX + 0.5,
        anchorY + 0.5,
        anchorZ)
    self.status = "Teleported to " .. button.outpost.name
        .. " " .. source .. " anchor."
end

function TGSRROutpostSurveyWindow:onInspectNearest()
    local player = getSpecificPlayer(0) or getPlayer()
    if not player then
        self.status = "No player is available."
        return
    end
    local outpost, distance = Outposts.getNearest(player:getX(), player:getY(), 150)
    if not outpost then
        self.status = "No registered outpost is within 150 tiles."
        return
    end
    Inspector.showFor(outpost)
    self.status = string.format("Inspecting %s (%.1f tiles away).", outpost.name, distance)
end

function TGSRROutpostSurveyWindow:onOutpostButton(button)
    self:openInspector(button.outpost, button.definition)
end

function TGSRROutpostSurveyWindow:updateCapturedButton(outpost)
    local button = self.buttons[outpost.id]
    if button then
        button.backgroundColor = { r = 0.1, g = 0.45, b = 0.15, a = 1 }
    end
end

function TGSRROutpostSurveyWindow:resurveySavedArea(outpost, definition)
    local savedRow = SurveyIO.loadAll()[outpost.id]
    if not savedRow then
        self.status = "No saved area exists for " .. outpost.name .. "."
        return
    end

    local success, message = captureOutpost(outpost, savedRow)
    self.status = message
    if success then
        self:updateCapturedButton(outpost)
        self:openInspector(outpost, definition)
    end
    print("[TGSRR Outpost Survey] " .. message)
end

function TGSRROutpostSurveyWindow:newSurveyOutpost(outpost)
    local success, message = captureOutpost(outpost)
    self.status = message
    if success then
        self:updateCapturedButton(outpost)
        if Inspector.instance then
            Inspector.instance:setVisible(false)
        end
        self:beginZoneEditor(outpost)
    end
    print("[TGSRR Outpost Survey] " .. message)
end

function TGSRROutpostSurveyWindow:render()
    ISCollapsableWindow.render(self)
    if self.isCollapsed then return end
    self:drawText(self.status or "", 10, self.height - 72, 1, 1, 1, 1, UIFont.Small)
    self:drawText("Output: " .. SurveyIO.getFilename(), 10, self.height - 53, 0.7, 0.7, 0.7, 1, UIFont.Small)
end

function TGSRROutpostSurveyWindow:savePosition()
    SurveyIO.saveWindowPosition(self:getX(), self:getY())
end

function TGSRROutpostSurveyWindow:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    self:savePosition()
end

function TGSRROutpostSurveyWindow:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    self:savePosition()
end

function TGSRROutpostSurveyWindow:close()
    self:savePosition()
    ISCollapsableWindow.close(self)
end

function TGSRROutpostSurveyWindow:new(x, y)
    local width, height = 430, 470
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.title = "TGSRR Outpost Survey"
    o.resizable = false
    o.pin = true
    return o
end

local function getOrCreateSurveyWindow()
    if TGSRROutpostSurveyWindow.instance then
        return TGSRROutpostSurveyWindow.instance
    end
    local width, height = 430, 470
    local x, y = SurveyIO.loadWindowPosition()
    if x == nil or y == nil then
        x = math.floor((getCore():getScreenWidth() - width) / 2)
        y = math.floor((getCore():getScreenHeight() - height) / 2)
    end
    x = math.max(0, math.min(x, getCore():getScreenWidth() - width))
    y = math.max(0, math.min(y, getCore():getScreenHeight() - height))
    local window = TGSRROutpostSurveyWindow:new(x, y)
    window:initialise()
    TGSRROutpostSurveyWindow.instance = window
    return window
end

local function toggleSurveyWindow()
    local window = getOrCreateSurveyWindow()
    if window:getIsVisible() then
        window:setVisible(false)
    else
        window:addToUIManager()
        window:setVisible(true)
        window:bringToTop()
    end
end

LauncherPalette.register("outposts", "TGSRR Outposts", toggleSurveyWindow, 40)
