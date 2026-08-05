require "ISUI/ISButton"
require "ISUI/ISCollapsableWindow"

local AlarmRuntime = require "TGSRR/Alarms/CustomDecayRuntime"
local State = require "TGSRR/Tracker/State"
local LauncherPalette = require "TGSRR/Debug/LauncherPalette"

local function debugEnabled()
    return isDebugEnabled and isDebugEnabled()
end

TGSRRAlarmDebugWindow = ISCollapsableWindow:derive("TGSRRAlarmDebugWindow")
TGSRRAlarmDebugWindow.instance = nil
local WIDTH = 520
local HEIGHT = 394
local MARGIN = 14

local function addButton(window, x, y, width, text, callback)
    local button = ISButton:new(x, y, width, 24, text, window, callback)
    button:initialise()
    window:addChild(button)
    return button
end

local function markNullified(record)
    if not record then return end
    record.pending = false
    record.live = false
    record.nullified = true
    record.expiryDay = nil
    record.queued = false
    record.fullyStreamed = false
    record.loadedChunks = nil
    record.totalChunks = nil
    record.missingChunks = nil
    record.chunkDiagnostic = "record removed by vanilla"
end

function TGSRRAlarmDebugWindow:createChildren()
    ISCollapsableWindow.createChildren(self)
    local gap = 8
    local y = self:titleBarHeight() + 182
    addButton(self, math.floor((self.width - 190) / 2), y, 190,
        "Browse Closest", self.onBrowseClosest)
    y = y + 32
    local navigationWidth = math.floor((self.width - MARGIN * 2
        - gap * 2) / 3)
    addButton(self, MARGIN, y, navigationWidth,
        "Previous", self.onPrevious)
    addButton(self, MARGIN + navigationWidth + gap, y, navigationWidth,
        "Next", self.onNext)
    self.teleportButton = addButton(self,
        MARGIN + (navigationWidth + gap) * 2, y,
        navigationWidth, "Teleport", self.onTeleport)

    y = y + 32
    local actionWidth = math.floor((self.width - MARGIN * 2 - gap) / 2)
    addButton(self, MARGIN, y, actionWidth,
        "Reset Live", self.onResetLive)
    addButton(self, MARGIN + actionWidth + gap, y, actionWidth,
        "Reset Expired", self.onResetExpired)

    y = y + 32
    addButton(self, math.floor((self.width - 160) / 2), y, 160,
        "Trigger Now", self.onTrigger)
    y = y + 32
    self.gridButton = addButton(self,
        math.floor((self.width - 190) / 2), y, 190,
        "Set Grid Online", self.onToggleGrid)
    self.index = 1
    self.status = "Ready."
    self:onRefresh()
end

function TGSRRAlarmDebugWindow:onBrowseClosest()
    local player = getSpecificPlayer(0) or getPlayer()
    if not player or not self.records or #self.records == 0 then return end

    local playerX = player:getX()
    local playerY = player:getY()
    local currentBuildingKey = AlarmRuntime.currentBuildingKey(player)
    local closestIndex
    local closestDistance
    for index, record in ipairs(self.records) do
        if not record.nullified and record.x ~= nil and record.y ~= nil then
            if currentBuildingKey
                    and tostring(record.key) == tostring(currentBuildingKey) then
                closestIndex = index
                closestDistance = 0
                break
            end

            local x1 = tonumber(record.x1)
            local y1 = tonumber(record.y1)
            local x2 = tonumber(record.x2)
            local y2 = tonumber(record.y2)
            local dx
            local dy
            if x1 and x2 then
                dx = playerX < x1 and x1 - playerX
                    or (playerX >= x2 and playerX - (x2 - 1) or 0)
            else
                dx = tonumber(record.x) - playerX
            end
            if y1 and y2 then
                dy = playerY < y1 and y1 - playerY
                    or (playerY >= y2 and playerY - (y2 - 1) or 0)
            else
                dy = tonumber(record.y) - playerY
            end
            local distance = dx * dx + dy * dy
            if closestDistance == nil or distance < closestDistance then
                closestDistance = distance
                closestIndex = index
            end
        end
    end

    if not closestIndex then
        self.status = "No active alarm BuildingDef found in the list."
        return
    end
    self.index = closestIndex
    self.selectedKey = self:current().key
    local latest = AlarmRuntime.inspectRecord(self.selectedKey)
    if latest then self.records[self.index] = latest end
    self:saveState()
    self.status = "Selected closest alarm BuildingDef (read-only)."
end

function TGSRRAlarmDebugWindow:onRefresh()
    local previous = self:current()
    local selectedKey = self.selectedKey or (previous and previous.key)
        or State.getValue("alarmDebug.selectedBuildingId", nil)
    self.records = AlarmRuntime.listDebugRecords()
    self.recordRevision = AlarmRuntime.getRecordRevision()
    if #self.records == 0 then
        self.index = 0
        self.status = "No vanilla alarm candidates found."
    else
        self.index = math.max(1, math.min(self.index or 1, #self.records))
        if selectedKey then
            local found = false
            for index, record in ipairs(self.records) do
                if tostring(record.key) == tostring(selectedKey) then
                    self.index = index
                    found = true
                    break
                end
            end
            if not found and previous
                    and tostring(previous.key) == tostring(selectedKey) then
                markNullified(previous)
                self.records[#self.records + 1] = previous
                self.index = #self.records
            end
        end
        self.selectedKey = self:current() and self:current().key or nil
        self.status = "World alarm candidate list refreshed."
    end
end

function TGSRRAlarmDebugWindow:update()
    ISCollapsableWindow.update(self)
    if self.recordRevision ~= AlarmRuntime.getRecordRevision() then
        local current = self:current()
        if current then
            local latest = AlarmRuntime.inspectRecord(current.key)
            if latest then
                self.records[self.index] = latest
            else
                markNullified(current)
            end
        end
        self.recordRevision = AlarmRuntime.getRecordRevision()
    end
    self:updateTeleportLock()
end

function TGSRRAlarmDebugWindow:updateTeleportLock()
    if not self.teleportButton then return end
    if not self.teleportLockKey then
        self.teleportButton:setEnable(true)
        self.teleportButton:setTitle("Teleport")
        return
    end

    local record = AlarmRuntime.inspectRecord(self.teleportLockKey)
    if record and record.pending == true then
        self.teleportButton:setEnable(false)
        self.teleportButton:setTitle("Waiting...")
        return
    end
    if not record and (not AlarmRuntime.recordExists
            or AlarmRuntime.recordExists(self.teleportLockKey)) then
        self.teleportButton:setEnable(false)
        self.teleportButton:setTitle("Waiting...")
        return
    end

    self.teleportLockKey = nil
    self.teleportButton:setEnable(true)
    self.teleportButton:setTitle("Teleport")
    self.status = "Validation complete. Teleport ready."
end

function TGSRRAlarmDebugWindow:current()
    return self.records and self.records[self.index] or nil
end

function TGSRRAlarmDebugWindow:onPrevious()
    if not self.records or #self.records == 0 then return end
    self.index = self.index - 1
    if self.index < 1 then self.index = #self.records end
    self.selectedKey = self:current().key
    self:saveState()
end

function TGSRRAlarmDebugWindow:onNext()
    if not self.records or #self.records == 0 then return end
    self.index = self.index + 1
    if self.index > #self.records then self.index = 1 end
    self.selectedKey = self:current().key
    self:saveState()
end

function TGSRRAlarmDebugWindow:onTeleport()
    local record = self:current()
    local player = getSpecificPlayer(0) or getPlayer()
    if self.teleportLockKey or not record or not player
            or not record.x or not record.y then return end
    local targetX = record.x + 0.5
    local targetY = record.y + 0.5
    local targetZ = record.z or 0
    local chunkState = record.totalChunks ~= nil
        and (tostring(record.loadedChunks) .. "/"
            .. tostring(record.totalChunks)) or "unavailable"
    print("[TGSRR Alarms] TELEPORT source=debug-ui"
        .. " id=" .. tostring(record.key)
        .. " from=" .. tostring(math.floor(player:getX())) .. ","
        .. tostring(math.floor(player:getY())) .. ","
        .. tostring(math.floor(player:getZ()))
        .. " target=" .. tostring(targetX) .. ","
        .. tostring(targetY) .. "," .. tostring(targetZ)
        .. " bounds=" .. tostring(record.x1) .. ","
        .. tostring(record.y1) .. "-" .. tostring(record.x2) .. ","
        .. tostring(record.y2)
        .. " expiryDay=" .. tostring(record.expiryDay or "none")
        .. " pending=" .. tostring(record.pending == true)
        .. " chunksBefore=" .. chunkState)
    player:teleportTo(targetX, targetY, targetZ)
    self.teleportLockKey = tostring(record.key)
    self.teleportButton:setEnable(false)
    self.teleportButton:setTitle("Waiting...")
    self.status = "Teleported. Waiting for alarm validation."
end

function TGSRRAlarmDebugWindow:onResetLive()
    local record = self:current()
    if not record then return end
    if record.pending or record.nullified then
        self.status = record.nullified
            and "Vanilla nullified this alarm; it cannot be reset."
            or "Load this building before resetting its alarm."
        return
    end
    AlarmRuntime.debugReset(record.key, true)
    self:onRefresh()
    self.status = "Alarm reset live through tomorrow."
end

function TGSRRAlarmDebugWindow:onResetExpired()
    local record = self:current()
    if not record then return end
    if record.pending or record.nullified then
        self.status = record.nullified
            and "Vanilla nullified this alarm; it cannot be reset."
            or "Load this building before resetting its alarm."
        return
    end
    AlarmRuntime.debugReset(record.key, false)
    self:onRefresh()
    self.status = "Alarm reset with an expired battery."
end

function TGSRRAlarmDebugWindow:onTrigger()
    local record = self:current()
    if not record then return end
    if record.pending or record.nullified then
        self.status = record.nullified
            and "Vanilla nullified this alarm; it cannot be triggered."
            or "Load this building before triggering its alarm."
        return
    end
    local fired = AlarmRuntime.debugTrigger(record.key)
    self:onRefresh()
    self.status = fired and "Alarm triggered." or
        "Not triggered. Reset live and teleport nearby first."
end

function TGSRRAlarmDebugWindow:onToggleGrid()
    local enabled, day = AlarmRuntime.debugToggleGrid()
    self.status = enabled
        and ("Electrical grid forced online through day "
            .. tostring(day) .. ".")
        or ("Electrical shutoff restored to day "
            .. tostring(day) .. ".")
end

function TGSRRAlarmDebugWindow:render()
    ISCollapsableWindow.render(self)
    if self.isCollapsed then return end
    local record = self:current()
    if record then
        local current = AlarmRuntime.inspectRecord(record.key)
        if current then
            self.records[self.index] = current
            record = current
        elseif AlarmRuntime.recordExists
                and not AlarmRuntime.recordExists(record.key) then
            markNullified(record)
        end
    end
    local count = self.records and #self.records or 0
    local textX = MARGIN
    local textY = self:titleBarHeight() + 10
    self:drawText("World alarm candidates: " .. tostring(count)
        .. "    Selected: " .. tostring(self.index or 0)
        .. " of " .. tostring(count),
        textX, textY, 1, 1, 1, 1, UIFont.Small)
    if record then
        self:drawText("Building ID: " .. tostring(record.key),
            textX, textY + 22, 0.85, 0.85, 0.85, 1, UIFont.Small)
        self:drawText("Position: " .. tostring(record.x) .. ", "
            .. tostring(record.y) .. ", " .. tostring(record.z or 0),
            textX, textY + 44, 0.85, 0.85, 0.85, 1, UIFont.Small)
        local player = getSpecificPlayer(0) or getPlayer()
        local currentBuildingKey = AlarmRuntime.currentBuildingKey(player)
        self:drawText("In Building: " .. tostring(currentBuildingKey or "none"),
            textX, textY + 66, 0.75, 0.85, 1, 1, UIFont.Small)
        local pendingText = record.queued and "PENDING VANILLA (QUEUED)"
            or record.fullyStreamed and "PENDING VANILLA (NOT QUEUED)"
            or "PENDING VANILLA (STREAMING)"
        local stateText = record.nullified and "NULLIFIED VANILLA"
            or record.pending and pendingText
            or record.triggered and "TRIGGERED"
            or (record.live and "LIVE" or "EXPIRED")
        local red = (record.pending or record.nullified) and 0.85
            or record.live and not record.triggered and 0.45 or 0.9
        local green = record.nullified and 0.45
            or record.pending and 0.75
            or record.live and not record.triggered and 0.9 or 0.55
        local expiryText = record.nullified and "removed by vanilla"
            or ("world day " .. tostring(record.expiryDay))
        self:drawText("Battery expiry: " .. expiryText,
            textX, textY + 88, red, green, 0.55, 1, UIFont.Small)
        self:drawText("Status: " .. stateText,
            textX, textY + 110, red, green, 0.55, 1, UIFont.Small)
        if record.totalChunks ~= nil then
            local chunkText = "Chunks: " .. tostring(record.loadedChunks)
                .. "/" .. tostring(record.totalChunks)
            if record.missingChunks and record.missingChunks ~= "" then
                chunkText = chunkText .. "  Missing: " .. record.missingChunks
            end
            if record.chunkDiagnostic then
                chunkText = chunkText .. "  (" .. record.chunkDiagnostic .. ")"
            end
            self:drawText(chunkText, textX, textY + 132,
                0.75, 0.8, 0.9, 1, UIFont.Small)
        else
            local chunkDiagnostic = record.nullified
                and "record removed by vanilla"
                or record.chunkDiagnostic
                or (record.pending and "BuildingDef not resolved")
                or "diagnostic unavailable"
            self:drawText("Chunks: unavailable (" .. chunkDiagnostic .. ")",
                textX, textY + 132, 0.75, 0.8, 0.9, 1, UIFont.Small)
        end
    end
    if self.gridButton then
        self.gridButton:setTitle(AlarmRuntime.debugGridOnline()
            and "Restore Grid Setting" or "Set Grid Online")
    end
    self:drawTextCentre(self.status or "", self.width / 2, self.height - 25,
        0.8, 0.8, 0.8, 1, UIFont.Small)
end

function TGSRRAlarmDebugWindow:saveState(open)
    local record = self:current()
    State.setValues({
        ["alarmDebug.x"] = math.floor(self:getX()),
        ["alarmDebug.y"] = math.floor(self:getY()),
        ["alarmDebug.open"] = open == true and "true" or
            (open == false and "false"
                or (self:getIsVisible() and "true" or "false")),
        ["alarmDebug.selectedBuildingId"] =
            record and tostring(record.key) or "",
    })
    State.flush()
end

function TGSRRAlarmDebugWindow:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    self:saveState()
end

function TGSRRAlarmDebugWindow:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    self:saveState()
end

function TGSRRAlarmDebugWindow:close()
    self:setVisible(false)
    self:saveState(false)
end

function TGSRRAlarmDebugWindow:new(x, y)
    local window = ISCollapsableWindow.new(self, x, y, WIDTH, HEIGHT)
    window.title = "TGSRR Alarm Test"
    window.resizable = false
    window.pin = true
    return window
end

local function toggleWindow()
    if not debugEnabled() then return end

    local window = TGSRRAlarmDebugWindow.instance
    if not window then
        local defaultX = math.floor(
            (getCore():getScreenWidth() - WIDTH) / 2)
        local defaultY = math.floor(
            (getCore():getScreenHeight() - HEIGHT) / 2)
        local x = tonumber(State.getValue("alarmDebug.x", defaultX))
            or defaultX
        local y = tonumber(State.getValue("alarmDebug.y", defaultY))
            or defaultY
        x = math.max(0, math.min(x,
            getCore():getScreenWidth() - WIDTH))
        y = math.max(0, math.min(y,
            getCore():getScreenHeight() - HEIGHT))
        window = TGSRRAlarmDebugWindow:new(
            x, y)
        window:initialise()
        window:setVisible(false)
        window:addToUIManager()
        TGSRRAlarmDebugWindow.instance = window
    end
    window:setVisible(not window:getIsVisible())
    if window:getIsVisible() then
        window:onRefresh()
        window:bringToTop()
    end
    window:saveState(window:getIsVisible())
end

local function restoreWindow()
    if State.getValue("alarmDebug.open", "false") == "true" then
        toggleWindow()
    end
end

if debugEnabled() then
    LauncherPalette.register("alarm", "TGSRR Alarm Test", toggleWindow, 10)
    Events.OnGameStart.Add(restoreWindow)
end

return TGSRRAlarmDebugWindow
