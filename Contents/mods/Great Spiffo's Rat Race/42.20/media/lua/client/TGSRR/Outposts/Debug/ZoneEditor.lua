require "ISUI/Animal/ISAddDesignationAnimalZoneUI"

local SurveyIO = require "TGSRR/Outposts/Debug/SurveyIO"
local ModalLayout = require "TGSRR/Run/ModalLayout"

local OutpostZoneEditor = ISAddDesignationAnimalZoneUI:derive("TGSRROutpostZoneEditor")

function OutpostZoneEditor:initialise()
    ISAddDesignationAnimalZoneUI.initialise(self)
    self.titleEntry:setName(self.outpost.name .. " Core Outpost Zone")
end

local function normaliseBounds(x1, y1, x2, y2)
    return math.min(x1, x2), math.min(y1, y2), math.max(x1, x2), math.max(y1, y2)
end

local function roomNames(def)
    local names = {}
    local rooms = def:getRooms()
    for index = 0, rooms:size() - 1 do
        local room = rooms:get(index)
        names[#names + 1] = tostring(room:getName() or "<unnamed>") .. "@" .. tostring(room:getZ())
    end
    table.sort(names)
    return table.concat(names, ",")
end

local function clearBuildingFields(row)
    for key, _ in pairs(row) do
        if tostring(key):match("^zoneBuilding%d+") then row[key] = nil end
    end
end

local function catalogueBuildings(row, minX, minY, maxX, maxY)
    clearBuildingFields(row)
    local buildings = ArrayList.new()
    getWorld():getMetaGrid():getBuildingsIntersecting(minX, minY, maxX - minX + 1, maxY - minY + 1, buildings)
    local values = {}
    for index = 0, buildings:size() - 1 do values[#values + 1] = buildings:get(index) end
    table.sort(values, function(a, b) return tostring(a:getIDString()) < tostring(b:getIDString()) end)
    row.zoneBuildingCount = #values
    for index, def in ipairs(values) do
        local prefix = "zoneBuilding" .. tostring(index)
        row[prefix .. "Id"] = tostring(def:getIDString())
        row[prefix .. "MinX"] = def:getX()
        row[prefix .. "MinY"] = def:getY()
        row[prefix .. "MaxX"] = def:getX2() - 1
        row[prefix .. "MaxY"] = def:getY2() - 1
        row[prefix .. "RoomCount"] = def:getRoomsNumber()
        row[prefix .. "Rooms"] = roomNames(def)
    end
end

function OutpostZoneEditor:finish(message)
    self:reset()
    self:setVisible(false)
    self:removeFromUIManager()
    self.parentUI.status = message
    self.parentUI:addToUIManager()
    self.parentUI:setVisible(true)
    self.parentUI:bringToTop()
end

function OutpostZoneEditor:undisplay()
    self:finish(self.outpost.name .. " zone selection cancelled.")
end

function OutpostZoneEditor:askCreateZone()
    if not self.drawTileMouse or not self.startingX or not self.startingY
            or not self.widthCorrect or not self.heightCorrect then
        self:undisplay()
        return
    end
    self.drawTileMouse = false
    self.waitingConfirm = true
    local width, height = 380, 150
    local text = "Save the " .. self.outpost.name .. " core outpost zone?"
    local x, y
    x, y, width, height =
        ModalLayout.fitAndCenter(width, height, text, self.playerNum)
    local modal = ISModalDialog:new(x, y, width, height,
        text,
        true, self, ISAddDesignationAnimalZoneUI.onCreateZone)
    modal:initialise()
    modal:addToUIManager()
    modal.modal = self
    modal.moveWithMouse = true
end

function OutpostZoneEditor:addZone()
    ISWorldObjectContextMenu.disableWorldMenu = false
    local minX, minY, maxX, maxY = normaliseBounds(self.startingX, self.startingY, self.endX, self.endY)
    local anchorX, anchorY = tonumber(self.row.playerX), tonumber(self.row.playerY)
    if anchorX < minX or anchorX > maxX or anchorY < minY or anchorY > maxY then
        self.statusMessage = "Zone must contain the captured church anchor."
        self:reset()
        self.drawTileMouse = true
        return
    end
    if minX < tonumber(self.row.clearanceMinX) or minY < tonumber(self.row.clearanceMinY)
            or maxX > tonumber(self.row.clearanceMaxX) or maxY > tonumber(self.row.clearanceMaxY) then
        self.statusMessage = "Zone must remain inside the 150x150 clearance cell."
        self:reset()
        self.drawTileMouse = true
        return
    end

    self.row.zoneMinX, self.row.zoneMinY = minX, minY
    self.row.zoneMaxX, self.row.zoneMaxY = maxX, maxY
    self.row.zoneWidth, self.row.zoneHeight = maxX - minX + 1, maxY - minY + 1
    catalogueBuildings(self.row, minX, minY, maxX, maxY)
    if not SurveyIO.saveSection(self.outpost.id, self.row, self.keyOrder) then
        self.statusMessage = "Could not save the outpost zone."
        return
    end
    self:finish(self.outpost.name .. " zone saved with " .. tostring(self.row.zoneBuildingCount) .. " mapped building(s).")
end

function OutpostZoneEditor:prerender()
    ISAddDesignationAnimalZoneUI.prerender(self)

    -- Vanilla livestock zones impose a 40x40 limit. TGSRR core zones may use
    -- any rectangle up to the full 150x150 clearance area.
    if self.startingX and self.startRenderTile then
        local minX, minY, maxX, maxY = normaliseBounds(self.startingX, self.startingY, self.endX, self.endY)
        local width, height = maxX - minX + 1, maxY - minY + 1
        self.widthCorrect = width >= 2 and width <= 150
        self.heightCorrect = height >= 2 and height <= 150

        if self.widthCorrect and self.heightCorrect then
            addAreaHighlightForPlayer(self.playerNum, minX, minY, maxX + 1, maxY + 1,
                self.player:getCurrentSquare():getZ(),
                self.zoneColor.r, self.zoneColor.g, self.zoneColor.b, self.zoneColor.a)
        end
    end

    self:drawText("TGSRR: " .. self.outpost.name .. " core zone", 10, 8, 1, 0.75, 0.25, 1, UIFont.Small)
    if self.statusMessage then
        self:drawText(self.statusMessage, 10, self.height - 48, 1, 0.25, 0.25, 1, UIFont.Small)
    end
end

function OutpostZoneEditor:new(x, y, width, height, player, parentUI, outpost, row, keyOrder)
    local o = ISAddDesignationAnimalZoneUI.new(self, x, y, width, height, player)
    o.parentUI = parentUI
    o.outpost = outpost
    o.row = row
    o.keyOrder = keyOrder
    o.zoneColor = { r = 1.0, g = 0.55, b = 0.1, a = 0.45 }
    return o
end

return OutpostZoneEditor
