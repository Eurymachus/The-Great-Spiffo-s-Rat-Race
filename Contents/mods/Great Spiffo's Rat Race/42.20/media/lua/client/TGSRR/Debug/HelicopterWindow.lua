require "ISUI/ISButton"
require "ISUI/ISCollapsableWindow"

local HelicopterScheduler = require "TGSRR/Core/HelicopterScheduler"
local HelicopterRuntime = require "TGSRR/Helicopter/Runtime"
local WindowState = require "TGSRR/Debug/HelicopterWindowState"
local LauncherPalette = require "TGSRR/Debug/LauncherPalette"

TGSRRHelicopterDebugWindow =
    ISCollapsableWindow:derive("TGSRRHelicopterDebugWindow")
TGSRRHelicopterDebugWindow.instance = nil

local function clockText(timeOfDay)
    local hour = math.floor(timeOfDay)
    local minute = math.floor((timeOfDay - hour) * 60 + 0.5)
    if minute >= 60 then
        hour = hour + 1
        minute = 0
    end
    return string.format("%02d:%02d", hour, minute)
end

function TGSRRHelicopterDebugWindow:createChildren()
    ISCollapsableWindow.createChildren(self)

    local buttonWidth = 140
    local buttonX = math.floor(
        (self.width - buttonWidth) / 2)
    local rowY = self:titleBarHeight() + 119
    self.refreshButton = ISButton:new(
        buttonX, rowY, buttonWidth, 26, "Refresh",
        self, self.onRefresh)
    self.refreshButton:initialise()
    self:addChild(self.refreshButton)

    self.jumpButton = ISButton:new(
        buttonX, rowY + 32, buttonWidth, 26, "Jump",
        self, self.onJump)
    self.jumpButton:initialise()
    self:addChild(self.jumpButton)

    self.status = "Ready."
    self:onRefresh()
end

function TGSRRHelicopterDebugWindow:onRefresh()
    HelicopterRuntime.update()
    self.schedule = HelicopterScheduler.read()
    local gameTime = getGameTime()
    self.currentDate = {
        year = gameTime:getYear(),
        month = gameTime:getMonth() + 1,
        day = gameTime:getDay() + 1,
        timeOfDay = gameTime:getTimeOfDay(),
    }
    self.scheduleDate = self.schedule
        and HelicopterScheduler.dateForDay(
            self.schedule.day, gameTime) or nil
    self.status = "Schedule refreshed."
end

function TGSRRHelicopterDebugWindow:onJump()
    self:onRefresh()
    local schedule = self.schedule
    if not schedule then
        self.status = "No helicopter schedule is available."
        return
    end
    if schedule.day < schedule.today then
        self.status = "The helicopter schedule is exhausted."
        return
    end

    local gameTime = getGameTime()
    local targetDate, dateError =
        HelicopterScheduler.dateForDay(schedule.day, gameTime)
    if not targetDate then
        self.status = "Could not resolve target date: "
            .. tostring(dateError)
        return
    end

    local targetHour = schedule.startHour - (70 / 60)
    local oldWorldAgeHours = gameTime:getWorldAgeHours()
    local targetWorldAgeHours = schedule.day * 24 + targetHour - 7
    if targetHour < 7 then
        targetWorldAgeHours = schedule.day * 24 + targetHour + 17
    end
    if targetWorldAgeHours <= oldWorldAgeHours then
        self.status = "The 1h 10m-before point has already passed."
        return
    end

    gameTime:setYear(targetDate.year)
    gameTime:setMonth(targetDate.month - 1)
    gameTime:setDay(targetDate.day - 1)
    gameTime:setNightsSurvived(schedule.day)
    gameTime:setTimeOfDay(targetHour)
    if gameTime.setLastTimeOfDay then
        gameTime:setLastTimeOfDay(targetHour)
    end
    gameTime:getCalender()

    local player = getSpecificPlayer(0) or getPlayer()
    if player and player.setHoursSurvived then
        local elapsed = targetWorldAgeHours - oldWorldAgeHours
        player:setHoursSurvived(
            player:getHoursSurvived() + elapsed)
    end

    self.status = string.format(
        "Jumped to %04d-%02d-%02d at %s.",
        targetDate.year,
        targetDate.month,
        targetDate.day,
        clockText(targetHour)
    )
    print("[TGSRR] " .. self.status)
end

function TGSRRHelicopterDebugWindow:render()
    ISCollapsableWindow.render(self)
    if self.isCollapsed then return end

    local schedule = self.schedule
    local current = self.currentDate
    local scheduled = self.scheduleDate
    self:drawText(
        "Current Day: "
            .. tostring(schedule and schedule.today or 0),
        10, self:titleBarHeight() + 8,
        1, 1, 1, 1, UIFont.Small)
    self:drawText(
        string.format(
            "Current Date: %04d-%02d-%02d at %s",
            current and current.year or 0,
            current and current.month or 0,
            current and current.day or 0,
            clockText(current and current.timeOfDay or 0)
        ),
        10, self:titleBarHeight() + 30,
        1, 1, 1, 1, UIFont.Small)
    self:drawText(
        string.format(
            "Helicopter Date: %04d-%02d-%02d (day %d)",
            scheduled and scheduled.year or 0,
            scheduled and scheduled.month or 0,
            scheduled and scheduled.day or 0,
            schedule and schedule.day or 0
        ),
        10, self:titleBarHeight() + 62,
        1, 1, 1, 1, UIFont.Small)
    self:drawText(
        string.format(
            "Helicopter Time: %02d:00-%02d:00",
            schedule and schedule.startHour or 0,
            schedule and schedule.endHour or 0
        ),
        10, self:titleBarHeight() + 84,
        1, 1, 1, 1, UIFont.Small)
    self:drawTextCentre(
        self.status or "",
        self.width / 2, self.height - 28,
        0.8, 0.8, 0.8, 1, UIFont.Small)
end

function TGSRRHelicopterDebugWindow:saveState(isOpen)
    WindowState.save(self, isOpen)
end

function TGSRRHelicopterDebugWindow:onMouseUp(x, y)
    ISCollapsableWindow.onMouseUp(self, x, y)
    self:saveState(self:getIsVisible())
end

function TGSRRHelicopterDebugWindow:onMouseUpOutside(x, y)
    ISCollapsableWindow.onMouseUpOutside(self, x, y)
    self:saveState(self:getIsVisible())
end

function TGSRRHelicopterDebugWindow:close()
    self:setVisible(false)
    self:saveState(false)
end

function TGSRRHelicopterDebugWindow:new(x, y)
    local window = ISCollapsableWindow.new(
        self, x, y, 400, 246)
    window.title = "TGSRR Helicopter Debug"
    window.resizable = false
    window.pin = true
    return window
end

local function getOrCreateWindow()
    if TGSRRHelicopterDebugWindow.instance then
        return TGSRRHelicopterDebugWindow.instance
    end

    local width, height = 400, 246
    local defaultX = math.floor(
        (getCore():getScreenWidth() - width) / 2)
    local defaultY = math.floor(
        (getCore():getScreenHeight() - height) / 2)
    local x, y = WindowState.position(defaultX, defaultY)
    x = math.max(0, math.min(
        x, getCore():getScreenWidth() - width))
    y = math.max(0, math.min(
        y, getCore():getScreenHeight() - height))
    local window = TGSRRHelicopterDebugWindow:new(x, y)
    window:initialise()
    window:setVisible(false)
    TGSRRHelicopterDebugWindow.instance = window
    return window
end

local function addWindow(window)
    if window.addedToUIManager then return end
    window:addToUIManager()
    window.addedToUIManager = true
end

local function toggleWindow()
    local window = getOrCreateWindow()
    if window:getIsVisible() then
        window:setVisible(false)
        window:saveState(false)
        return
    end
    addWindow(window)
    window:setVisible(true)
    window:bringToTop()
    window:onRefresh()
    window:saveState(true)
end

local function restoreWindow()
    local window = getOrCreateWindow()
    addWindow(window)
    if WindowState.isOpen() then
        window:setVisible(true)
        window:bringToTop()
        window:onRefresh()
    else
        window:setVisible(false)
    end
end

LauncherPalette.register("helicopter", "TGSRR Helicopter", toggleWindow, 20)
Events.OnGameStart.Add(restoreWindow)

return TGSRRHelicopterDebugWindow
