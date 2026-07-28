local ClockCheckpoint = require "TGSRR/Run/ClockCheckpoint"

local ClockReconciler = {}

local HOUR_TOLERANCE = 2 / 60

local function leapYear(year)
    return year % 4 == 0 and (year % 100 ~= 0 or year % 400 == 0)
end

local function daysInMonth(year, month)
    if month == 2 then return leapYear(year) and 29 or 28 end
    if month == 4 or month == 6 or month == 9 or month == 11 then
        return 30
    end
    return 31
end

local function addDays(calendar, count)
    local year = math.floor(tonumber(calendar.year) or 0)
    local month = math.floor(tonumber(calendar.month) or 1)
    local day = math.floor(tonumber(calendar.day) or 1)
    for _ = 1, math.max(0, math.floor(count)) do
        day = day + 1
        if day > daysInMonth(year, month) then
            day = 1
            month = month + 1
            if month > 12 then
                month = 1
                year = year + 1
            end
        end
    end
    return { year = year, month = month, day = day }
end

local function calendar(gameTime)
    return {
        year = tonumber(gameTime:getYear()) or 0,
        month = (tonumber(gameTime:getMonth()) or 0) + 1,
        day = (tonumber(gameTime:getDay()) or 0) + 1,
    }
end

local function sameCalendar(a, b)
    return tonumber(a and a.year) == tonumber(b and b.year)
        and tonumber(a and a.month) == tonumber(b and b.month)
        and tonumber(a and a.day) == tonumber(b and b.day)
end

local function close(a, b)
    return math.abs((tonumber(a) or 0) - (tonumber(b) or 0))
        <= HOUR_TOLERANCE
end

function ClockReconciler.expected(anchor, playerHours)
    local delta = (tonumber(playerHours) or 0)
        - (tonumber(anchor.playerHoursSurvived) or 0)
    if delta < -HOUR_TOLERANCE then
        return nil, "player_hours_regressed"
    end
    delta = math.max(0, delta)
    local totalTime = (tonumber(anchor.timeOfDay) or 0) + delta
    local elapsedDays = math.floor(totalTime / 24)
    local timeOfDay = totalTime - elapsedDays * 24
    local worldAgeHours =
        (tonumber(anchor.worldAgeHours) or 0) + delta
    local worldDayOffset = timeOfDay >= 7
        and timeOfDay - 7 or timeOfDay + 17
    local nightsSurvived = math.max(0, math.floor(
        (worldAgeHours - worldDayOffset) / 24 + 0.5))
    return {
        calendar = addDays(anchor.calendar, elapsedDays),
        timeOfDay = timeOfDay,
        nightsSurvived = nightsSurvived,
        worldAgeHours = worldAgeHours,
        playerHoursSurvived = tonumber(playerHours) or 0,
        elapsedHours = delta,
    }
end

function ClockReconciler.inspect(run, player, anchor, gameTime)
    if not anchor then return { status = "unanchored" } end
    if tonumber(anchor.eventSequence) ~= tonumber(run.eventSequence)
            or tostring(anchor.eventHash or ""):lower()
                ~= tostring(run.eventHash or ""):lower() then
        return { status = "checkpoint_cursor_mismatch" }
    end
    gameTime = gameTime or (getGameTime and getGameTime() or nil)
    if not gameTime or not player then
        return nil, "clock_reconciliation_unavailable"
    end
    local observed = {
        calendar = calendar(gameTime),
        timeOfDay = tonumber(gameTime:getTimeOfDay()) or 0,
        nightsSurvived = math.max(0,
            math.floor(tonumber(gameTime:getNightsSurvived()) or 0)),
        worldAgeHours = math.max(0,
            tonumber(gameTime:getWorldAgeHours()) or 0),
        playerHoursSurvived = math.max(0,
            tonumber(player:getHoursSurvived()) or 0),
    }
    local expected, expectedError =
        ClockReconciler.expected(anchor, observed.playerHoursSurvived)
    if not expected then
        return {
            status = "ambiguous",
            reason = expectedError,
            anchor = anchor,
            observed = observed,
        }
    end
    local consistent = sameCalendar(observed.calendar, expected.calendar)
        and close(observed.timeOfDay, expected.timeOfDay)
        and observed.nightsSurvived == expected.nightsSurvived
        and close(observed.worldAgeHours, expected.worldAgeHours)
    return {
        status = consistent and "consistent" or "repair_required",
        anchor = anchor,
        observed = observed,
        expected = expected,
    }
end

function ClockReconciler.apply(reconciliation, gameTime)
    if not reconciliation
            or reconciliation.status ~= "repair_required" then
        return false, "clock_repair_not_required"
    end
    gameTime = gameTime or (getGameTime and getGameTime() or nil)
    if not gameTime then return false, "clock_repair_unavailable" end
    local expected = reconciliation.expected
    gameTime:setYear(expected.calendar.year)
    gameTime:setMonth(expected.calendar.month - 1)
    gameTime:setDay(expected.calendar.day - 1)
    gameTime:setNightsSurvived(expected.nightsSurvived)
    gameTime:setTimeOfDay(expected.timeOfDay)
    if gameTime.setLastTimeOfDay then
        gameTime:setLastTimeOfDay(expected.timeOfDay)
    end
    local repaired = {
        calendar = calendar(gameTime),
        timeOfDay = tonumber(gameTime:getTimeOfDay()) or 0,
        nightsSurvived = math.max(0,
            math.floor(tonumber(gameTime:getNightsSurvived()) or 0)),
        worldAgeHours = math.max(0,
            tonumber(gameTime:getWorldAgeHours()) or 0),
    }
    if not sameCalendar(repaired.calendar, expected.calendar)
            or not close(repaired.timeOfDay, expected.timeOfDay)
            or repaired.nightsSurvived ~= expected.nightsSurvived
            or not close(repaired.worldAgeHours, expected.worldAgeHours) then
        return false, "clock_repair_readback_failed"
    end
    reconciliation.repaired = repaired
    return true, reconciliation
end

function ClockReconciler.initialize(run, player)
    local anchor = ClockCheckpoint.initialize(run, player)
    return ClockReconciler.inspect(run, player, anchor)
end

ClockReconciler.HOUR_TOLERANCE = HOUR_TOLERANCE
ClockReconciler.addDays = addDays

return ClockReconciler
