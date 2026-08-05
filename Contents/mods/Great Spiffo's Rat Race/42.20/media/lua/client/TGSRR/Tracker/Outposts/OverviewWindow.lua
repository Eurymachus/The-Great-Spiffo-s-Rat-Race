require "ISUI/ISCollapsableWindow"
require "ISUI/ISScrollingListBox"
require "ISUI/ISButton"

local Snapshot = require "TGSRR/Tracker/Outposts/Snapshot"
local Outposts = require "TGSRR/Outposts/Definitions"
local L = require "TGSRR/Core/Localization"
local Icons = require "TGSRR/Tracker/Outposts/Icons"
local Notifications = require "TGSRR/Challenge/Notifications"
local State = require "TGSRR/Tracker/State"
local Identity = require "TGSRR/Run/Identity"
local LandmarkMap = require "TGSRR/Tracker/Landmarks/WorldMap"

local Window = ISCollapsableWindow:derive("TGSRROutpostOverviewWindow")
Window.instance = nil

local WIDTH = 640
local HEIGHT = 650
local MARGIN = 12
local HEADER_HEIGHT = 112
local COLUMN_VALUE_X = 0.58
local COLUMN_STATUS_X = 0.80
local REFRESH_INTERVAL_MS = 1000
local HELP_ICON = getTexture("media/ui/foraging/questionMark.png")
local CHECK_ICON = getTexture("media/ui/inventoryPanes/Tickbox_Tick.png")
local CROSS_ICON = getTexture("media/ui/inventoryPanes/Tickbox_Cross.png")
local HELP_ICON_SIZE = 14
local STATUS_ICON_SIZE = 18
local MAP_BUTTON_SIZE = 44
local MAP_ICON_SIZE = 34
local MAP_ICON = getTexture("media/textures/worldMap/Map_On.png")
local function loadWindowState()
    local state = State.load()
    local x = tonumber(state["outpostOverview.x"])
    local y = tonumber(state["outpostOverview.y"])
    if not x or not y then return nil end
    return {
        x = x,
        y = y,
        open = state["outpostOverview.open"],
        outpostId = state["outpostOverview.outpostId"],
    }
end

local function saveWindowState(window, open)
    State.setValues({
        ["outpostOverview.x"] = math.floor(window:getX()),
        ["outpostOverview.y"] = math.floor(window:getY()),
        ["outpostOverview.open"] = open == true and "true" or "false",
        ["outpostOverview.outpostId"] = window.outpost and window.outpost.id or "",
    })
end

local function statusText(status)
    if status == "passed" then return L.text("UI_TGSRR_Tracker_Passed", "Passed") end
    if status == "pending" then return L.text("UI_TGSRR_Tracker_Pending", "Pending") end
    return L.text("UI_TGSRR_Tracker_Unavailable", "Unavailable")
end

local function requirement(labelKey, fallback, tooltipKey, tooltipFallback, value, status, tooltip)
    return {
        label = L.text(labelKey, fallback),
        tooltip = tooltip or L.text(tooltipKey, tooltipFallback),
        value = value or "-",
        status = status or "unavailable",
    }
end

local function roundedPercent(value)
    return tostring(math.floor((tonumber(value) or 0) + 0.5)) .. "%"
end

local function spareCarTooltip(deliverable)
    local base = L.text("UI_TGSRR_Tracker_Tooltip_SpareCar",
        "Park a qualifying spare car within the outpost's support area.")
    local details = deliverable and deliverable.details or nil
    local facts = details and details.vehicle or nil
    local failures = details and details.failures or nil
    if not facts or type(failures) ~= "table" or #failures == 0 then return base end

    local target = "75% " .. L.text("UI_TGSRR_Tracker_Required", "required")
    local labels = {
        engine = L.text("UI_TGSRR_Vehicle_EngineCondition", "Engine condition"),
        fuel = L.text("UI_TGSRR_Vehicle_Fuel", "Fuel"),
        battery_condition = L.text("UI_TGSRR_Vehicle_BatteryCondition", "Battery condition"),
        battery_charge = L.text("UI_TGSRR_Vehicle_BatteryCharge", "Battery charge"),
        driver_seat = L.text("UI_TGSRR_Vehicle_DriverSeat", "Driver's seat"),
        tyres = L.text("UI_TGSRR_Vehicle_Tyres", "Tyres"),
    }
    local values = {
        engine = facts.engine and facts.engine.condition or 0,
        fuel = facts.fuel and facts.fuel.percent or 0,
        battery_condition = facts.battery and facts.battery.condition or 0,
        battery_charge = facts.battery and facts.battery.charge or 0,
        driver_seat = facts.driverSeat and facts.driverSeat.condition or 0,
    }
    local lines = {
        L.text("UI_TGSRR_Vehicle_DoesNotQualify", "This vehicle does not qualify:"),
    }
    for _, failure in ipairs(failures) do
        local id, partId = tostring(failure):match("^([^:]+):?(.*)$")
        local label = labels[id]
        local value = values[id]
        if id == "tyre_condition" or id == "tyre_pressure" then
            local tyre = facts.parts and facts.parts[partId] or nil
            local tyreName = getTextOrNull("IGUI_VehiclePart" .. partId)
                or partId:gsub("Tire", ""):gsub("(%l)(%u)", "%1 %2")
            local suffix = id == "tyre_condition"
                and L.text("UI_TGSRR_Vehicle_Condition", "condition")
                or L.text("UI_TGSRR_Vehicle_Pressure", "pressure")
            label = tyreName .. " " .. suffix
            value = tyre and (id == "tyre_condition" and tyre.condition or tyre.pressurePercent) or 0
        end
        if label then
            lines[#lines + 1] = "- " .. label .. ": " .. roundedPercent(value) .. " / " .. target
        end
    end
    return table.concat(lines, "\n")
end

local function buildRequirements(row)
    local activation = row.activation
    local runtime = row.runtime or {}
    local deliverables = runtime.deliverables or {}
    local clearance = deliverables.zombie_clearance
    local windows = deliverables.window_barricades
    local enclosed = deliverables.enclosed
    local doorsFitted = deliverables.doors_fitted
    local doorsClosed = deliverables.doors_closed
    local goodBed = deliverables.good_bed
    local generator = deliverables.generator
    local food = deliverables.food
    local plumbedSink = deliverables.plumbed_sink
    local spareCar = deliverables.spare_car
    local discovered = runtime.discovered == true
    local activationPassed = activation and activation.passed == true
    local windowValue = windows and
        (tostring(windows.current) .. " / " .. tostring(windows.required)) or "-"
    local enclosedValue = enclosed and
        (tostring(enclosed.current) .. " / " .. tostring(enclosed.required)) or "-"
    local doorsFittedValue = doorsFitted and
        (tostring(doorsFitted.current) .. " / " .. tostring(doorsFitted.required)) or "-"
    local doorsValue = doorsClosed and
        (tostring(doorsClosed.current) .. " / " .. tostring(doorsClosed.required)) or "-"
    local goodBedValue = goodBed and
        (tostring(goodBed.current) .. " / " .. tostring(goodBed.required)) or "-"
    local generatorValue = L.text("UI_TGSRR_Tracker_None", "None")
    if generator and generator.state == "not_connected" then
        generatorValue = L.text("UI_TGSRR_Tracker_NotConnected", "Not Connected")
    elseif generator and generator.state == "fuel" then
        generatorValue = L.text("UI_TGSRR_Tracker_Fuel", "Fuel") .. ": " ..
            tostring(math.floor((generator.current or 0) + 0.5)) .. "%"
    end
    local sinkValue = L.text("UI_TGSRR_Tracker_None", "None")
    if plumbedSink and plumbedSink.state == "not_plumbed" then
        sinkValue = L.text("UI_TGSRR_Tracker_NotPlumbed", "Not Plumbed")
    elseif plumbedSink and plumbedSink.state == "source_missing" then
        sinkValue = L.text("UI_TGSRR_Tracker_WaterSourceMissing", "Water Source Missing")
    elseif plumbedSink and plumbedSink.state == "connected" then
        sinkValue = L.text("UI_TGSRR_Tracker_Connected", "Connected")
    end
    local spareCarValue = L.text("UI_TGSRR_Tracker_None", "None")
    if spareCar and spareCar.state == "ready" then
        spareCarValue = L.text("UI_TGSRR_Tracker_Ready", "Ready")
    elseif spareCar and spareCar.state == "requirements_unmet" then
        spareCarValue = L.text("UI_TGSRR_Tracker_NeedsRepairs", "Needs repairs")
    end

    local result = {
        requirement("UI_TGSRR_Tracker_Discovery", "Discovery",
            "UI_TGSRR_Tracker_Tooltip_Discovery", "Enter the outpost's 150 x 150 clearance area.", nil,
            discovered and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_RoomActivation", "Room activation",
            "UI_TGSRR_Tracker_Tooltip_RoomActivation", "Visit every required accessible room in the outpost.",
            activation and (tostring(activation.activatedRooms) .. " / " .. tostring(activation.totalRooms)) or "-",
            activationPassed and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_FloorActivation", "Floor activation",
            "UI_TGSRR_Tracker_Tooltip_FloorActivation", "Activate every required floor, including registered basements.",
            activation and (tostring(activation.activatedFloors) .. " / " .. tostring(activation.totalFloors)) or "-",
            activationPassed and "passed" or "pending"),
        requirement("UI_TGSRR_Tracker_AreaCleared", "Area Cleared",
            "UI_TGSRR_Tracker_Tooltip_AreaCleared",
            "Clearing the area will Latch this deliverable and once latched it will not regress.\nIf the dead return it will be up to you to deal with them and keep the area safe.",
            nil, clearance and (clearance.passed and "passed" or "pending") or "pending"),
        requirement("UI_TGSRR_Tracker_WindowBarricades", "Window barricades",
            "UI_TGSRR_Tracker_Tooltip_WindowBarricades", "Barricade every ground-floor exterior window with wood, sheet metal, or metal bars.",
            windowValue, windows and (windows.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_ExteriorWalls", "Enclosed",
            "UI_TGSRR_Tracker_Tooltip_Enclosed", "Seal every ground-floor exterior edge with a wall, window opening, or doorway containing a door.",
            enclosedValue, enclosed and (enclosed.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_DoorsFitted", "Doors fitted",
            "UI_TGSRR_Tracker_Tooltip_DoorsFitted", "Fit a door into every ground-floor exterior door frame.",
            doorsFittedValue, doorsFitted and (doorsFitted.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_ExteriorDoors", "Doors closed",
            "UI_TGSRR_Tracker_Tooltip_DoorsClosed", "Close every ground-floor exterior door. Missing doors cannot pass.",
            doorsValue, doorsClosed and (doorsClosed.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_GoodBed", "Good bed",
            "UI_TGSRR_Tracker_Tooltip_GoodBed", "Provide a bed that offers Good sleep quality in a registered ground-floor outpost room.",
            goodBedValue, goodBed and (goodBed.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_Generator", "Generator",
            "UI_TGSRR_Tracker_Tooltip_Generator", "Place and connect a fully fuelled generator within the outpost boundary.",
            generatorValue, generator and (generator.passed and "passed" or "pending") or "pending"),
        requirement("UI_TGSRR_Tracker_Food", "Food",
            "UI_TGSRR_Tracker_Tooltip_Food", "Store at least 5,000 calories of non-spoilable food in containers within registered ground-floor outpost rooms.",
            food and (tostring(food.current) .. " / " .. tostring(food.required)) or "-",
            food and (food.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_PlumbedSink", "Sink",
            "UI_TGSRR_Tracker_Tooltip_PlumbedSink", "Provide a plumbed sink with its external water source still installed within a registered ground-floor outpost room.",
            sinkValue,
            plumbedSink and (plumbedSink.passed and "passed" or "pending") or "unavailable"),
        requirement("UI_TGSRR_Tracker_SpareCar", "Spare car",
            "UI_TGSRR_Tracker_Tooltip_SpareCar", "Park a qualifying spare car within the outpost's support area.",
            spareCarValue, spareCar and (spareCar.passed and "passed" or "pending") or "unavailable",
            spareCarTooltip(spareCar)),
    }
    result[4].binaryStatus = true
    return result
end

local function findRow(outpost)
    local snapshot = Snapshot.getAll(getSpecificPlayer(0) or getPlayer())
    for _, row in ipairs(snapshot.rows) do
        if row.id == outpost.id then return row end
    end
    return nil
end

function Window:createChildren()
    ISCollapsableWindow.createChildren(self)
    local mapY = self:titleBarHeight() + 10
    self.mapButton = ISButton:new(
        self.width - MARGIN - MAP_BUTTON_SIZE, mapY,
        MAP_BUTTON_SIZE, MAP_BUTTON_SIZE, "", self, Window.onMap)
    self.mapButton:initialise()
    self.mapButton:instantiate()
    self.mapButton:setImage(MAP_ICON)
    self.mapButton:forceImageSize(MAP_ICON_SIZE, MAP_ICON_SIZE)
    self.mapButton:setTooltip(L.text(
        "UI_TGSRR_Tracker_ViewOnMap", "View outpost on world map"))
    self:addChild(self.mapButton)

    local top = self:titleBarHeight() + HEADER_HEIGHT
    self.list = ISScrollingListBox:new(MARGIN, top, self.width - MARGIN * 2,
        self.height - top - MARGIN)
    self.list:initialise()
    self.list:instantiate()
    self.list.itemheight = 36
    self.list.doDrawItem = self.drawRequirement
    self.list.updateTooltip = Window.updateRequirementTooltip
    self.list.drawBorder = true
    self:addChild(self.list)
    self:refresh()
end

function Window:onMap()
    if self.outpost then LandmarkMap.showAt(self.outpost.anchor, 0) end
end

function Window:prerender()
    ISCollapsableWindow.prerender(self)
    if not self.row then return end

    local top = self:titleBarHeight() + 10
    local icon = Icons.get(self.row.outpost)
    local iconR, iconG, iconB = Icons.getColor(self.row.status, self.row.complete)
    if icon then self:drawTextureScaledAspect(icon, MARGIN, top, 54, 54, 1, iconR, iconG, iconB) end

    self:drawText(self.row.title, 78, top + 2, 1, 1, 1, 1, UIFont.Large)
    local stage = self.row.complete and L.text("UI_TGSRR_Tracker_Stage_Complete", "Complete") or
        (self.row.status == "in_progress" and
            L.text("UI_TGSRR_Tracker_Stage_InProgress", "In Progress") or
        (self.row.status == "undiscovered" and
            L.text("UI_TGSRR_Tracker_Stage_Undiscovered", "Undiscovered") or
            L.text("UI_TGSRR_Tracker_Stage_Discovered", "Discovered")))
    self:drawText(L.text("UI_TGSRR_Tracker_Stage", "Stage") .. ": " .. stage,
        78, top + 34, 0.76, 0.76, 0.76, 1, UIFont.Small)

    local barX, barY = MARGIN, top + 68
    local barWidth = self.width - MARGIN * 2
    self:drawRect(barX, barY, barWidth, 22, 0.8, 0.02, 0.02, 0.02)
    if self.row.percent > 0 then
        self:drawRect(barX + 1, barY + 1,
            math.floor((barWidth - 2) * self.row.percent / 100), 20,
            0.76, 0.12, 0.58, 0.18)
    end
    self:drawRectBorder(barX, barY, barWidth, 22, 0.62, 0.55, 0.55, 0.55)
    local progressTextY = barY + math.floor((22 - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawTextCentre(L.text("UI_TGSRR_Tracker_Progress", "Progress") .. ": " ..
        tostring(self.row.percent) .. "%", barX + barWidth / 2, progressTextY,
        1, 1, 1, 1, UIFont.Small)
end

function Window:drawRequirement(y, item, alt)
    local data = item.item
    local width = self:getWidth() - (self:isVScrollBarVisible() and self.vscroll:getWidth() or 0)
    if item.index % 2 == 0 then self:drawRect(0, y, width, self.itemheight - 1, 0.2, 0.12, 0.12, 0.12) end
    self:drawRect(0, y + self.itemheight - 1, width, 1, 0.32, 0.5, 0.5, 0.5)
    local textY = y + math.floor((self.itemheight - getTextManager():getFontHeight(UIFont.Small)) / 2)
    self:drawText(data.label, 8, textY, 1, 1, 1, 1, UIFont.Small)
    if data.binaryStatus then
        local helpX = 8 + getTextManager():MeasureStringX(UIFont.Small, data.label) + 6
        local helpY = y + math.floor((self.itemheight - HELP_ICON_SIZE) / 2)
        self:drawTextureScaledAspect(HELP_ICON, helpX, helpY,
            HELP_ICON_SIZE, HELP_ICON_SIZE, 0.9, 1, 1, 1)

        local statusX = math.floor(width * (COLUMN_STATUS_X + 1) / 2)
        local statusY = y + math.floor((self.itemheight - STATUS_ICON_SIZE) / 2)
        local icon = data.status == "passed" and CHECK_ICON or CROSS_ICON
        self:drawTextureScaledAspect(icon, statusX - math.floor(STATUS_ICON_SIZE / 2), statusY,
            STATUS_ICON_SIZE, STATUS_ICON_SIZE, 1, 1, 1, 1)
        return y + self.itemheight
    end
    self:drawTextCentre(data.value, math.floor(width * (COLUMN_VALUE_X + COLUMN_STATUS_X) / 2),
        textY, 0.82, 0.82, 0.82, 1, UIFont.Small)
    local colors = { passed = { 0.42, 0.9, 0.48 }, pending = { 1, 0.75, 0.24 },
        unavailable = { 0.55, 0.55, 0.55 } }
    local color = colors[data.status] or colors.unavailable
    self:drawTextCentre(statusText(data.status), math.floor(width * (COLUMN_STATUS_X + 1) / 2),
        textY, color[1], color[2], color[3], 1, UIFont.Small)
    return y + self.itemheight
end

function Window.updateRequirementTooltip(list)
    local row = list:rowAt(getMouseX(), getMouseY())
    local item = list.items[row]
    if item and item.item and item.item.binaryStatus then
        local data = item.item
        local localX = getMouseX() - list:getAbsoluteX()
        local helpX = 8 + getTextManager():MeasureStringX(UIFont.Small, data.label) + 6
        if localX >= helpX and localX < helpX + HELP_ICON_SIZE then
            item.tooltip = data.tooltip
        else
            item.tooltip = nil
        end
    end
    ISScrollingListBox.updateTooltip(list)
end

function Window:refresh()
    self.row = self.outpost and findRow(self.outpost) or nil
    if not self.row or not self.list then return end
    local requirements = buildRequirements(self.row)
    if #self.list.items ~= #requirements then
        self.list:clear()
        for _, entry in ipairs(requirements) do self.list:addItem(entry.label, entry, entry.tooltip) end
    else
        for index, entry in ipairs(requirements) do
            self.list.items[index].text = entry.label
            self.list.items[index].item = entry
            self.list.items[index].tooltip = entry.tooltip
        end
    end
    self.lastRefreshMs = getTimestampMs()
end

function Window:update()
    ISCollapsableWindow.update(self)
    if not self:getIsVisible() then return end
    local now = getTimestampMs()
    if not self.lastRefreshMs or now - self.lastRefreshMs >= REFRESH_INTERVAL_MS then self:refresh() end
end

function Window:close()
    saveWindowState(self, false)
    self:setVisible(false)
end

function Window:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    saveWindowState(self, self:getIsVisible())
end

function Window:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    saveWindowState(self, self:getIsVisible())
end

function Window:new(x, y, width, height, outpost)
    local o = ISCollapsableWindow.new(self, x, y, width, height)
    o.title = L.text("UI_TGSRR_Tracker_OutpostOverview", "Outpost Overview")
    o.outpost = outpost
    o.resizable = false
    o:setResizable(false)
    return o
end

function Window.showFor(outpost)
    local window = Window.instance
    if not window then
        local width = math.min(WIDTH, getCore():getScreenWidth())
        local height = math.min(HEIGHT, getCore():getScreenHeight())
        local state = loadWindowState()
        local x = state and state.x or math.floor((getCore():getScreenWidth() - width) / 2)
        local y = state and state.y or math.floor((getCore():getScreenHeight() - height) / 2)
        x = math.max(0, math.min(x, getCore():getScreenWidth() - width))
        y = math.max(0, math.min(y, getCore():getScreenHeight() - height))
        window = Window:new(x, y, width, height, outpost)
        window:initialise()
        Window.instance = window
    else
        window.outpost = outpost
        window:refresh()
    end
    window:addToUIManager()
    window:setVisible(true)
    window:bringToTop()
    saveWindowState(window, true)
    return window
end

Notifications.subscribe("outpost-overview-window", function(outpostId)
    local window = Window.instance
    if window and window:getIsVisible() and window.outpost and window.outpost.id == outpostId then
        window:refresh()
    end
end)

local function isRatRace()
    return Identity.isRatRaceChallenge()
end

Events.OnGameStart.Add(function()
    if not isRatRace() then return end
    local state = loadWindowState()
    if not state or state.open ~= "true" or not state.outpostId then return end
    local outpost = Outposts.get(state.outpostId)
    if outpost then Window.showFor(outpost) end
end)

return Window
