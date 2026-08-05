local HelicopterScheduler = require "TGSRR/Core/HelicopterScheduler"

local BasicSchedule = {
    id = "tgsrr_basic_v3",
}

local function boundedInteger(value, minimum, maximum, fallback)
    value = math.floor(tonumber(value) or fallback)
    return math.max(minimum, math.min(value, maximum))
end

local function normalize(source)
    if type(source) ~= "table" then
        return nil, "helicopter_schedule_missing"
    end

    local config = {
        enabled = source.Enabled ~= false,
        dayMinimum = boundedInteger(
            source.DayMinimum, 0, 31, 6),
        dayMaximum = boundedInteger(
            source.DayMaximum, 1, 32, 10),
        startHourMinimum = boundedInteger(
            source.StartHourMinimum, 0, 23, 9),
        startHourMaximum = boundedInteger(
            source.StartHourMaximum, 0, 23, 18),
        durationMinimum = boundedInteger(
            source.DurationMinimum, 1, 24, 1),
        durationMaximum = boundedInteger(
            source.DurationMaximum, 1, 24, 4),
        monthsByYear = {},
        slots = {},
    }
    if config.dayMaximum <= config.dayMinimum then
        return nil, "invalid_helicopter_day_range"
    end
    if config.startHourMaximum < config.startHourMinimum then
        return nil, "invalid_helicopter_start_hour_range"
    end
    if config.durationMaximum < config.durationMinimum then
        return nil, "invalid_helicopter_duration_range"
    end

    local sourceYears = source.MonthsByYear
    if type(sourceYears) ~= "table" then
        return nil, "helicopter_schedule_years_missing"
    end

    local years = {}
    for challengeYear, months in pairs(sourceYears) do
        challengeYear = math.floor(tonumber(challengeYear) or 0)
        if challengeYear >= 1 and type(months) == "table" then
            years[#years + 1] = challengeYear
        end
    end
    table.sort(years)

    for _, challengeYear in ipairs(years) do
        local normalizedMonths = {}
        for _, value in ipairs(sourceYears[challengeYear]) do
            local month = math.floor(tonumber(value) or 0)
            if month < 1 or month > 12 then
                return nil, "invalid_helicopter_month"
            end
            normalizedMonths[#normalizedMonths + 1] = month
            config.slots[#config.slots + 1] = {
                challengeYear = challengeYear,
                month = month,
            }
        end
        config.monthsByYear[challengeYear] = normalizedMonths
    end

    return config
end

local function parseMonthList(value)
    local text = tostring(value or "")
    if text:match("^%s*$") then return {} end

    local months = {}
    for token in (text .. ","):gmatch("(.-),") do
        local trimmed = token:match("^%s*(.-)%s*$")
        if trimmed == "" then return nil, "invalid_helicopter_month" end

        local month = tonumber(trimmed)
        if month == nil then return nil, "invalid_helicopter_month" end
        months[#months + 1] = month
    end
    return months
end

local function registeredSource(source)
    if type(source) ~= "table" then return nil end

    local years = {}
    for challengeYear = 1, 9 do
        local months, monthError = parseMonthList(
            source["Year" .. challengeYear .. "Months"])
        if not months then return nil, monthError end
        if #months > 0 then years[challengeYear] = months end
    end
    return {
        Enabled = source.Enabled == true,
        MonthsByYear = years,
        DayMinimum = source.DayMinimum,
        DayMaximum = source.DayMaximum,
        StartHourMinimum = source.StartHourMinimum,
        StartHourMaximum = source.StartHourMaximum,
        DurationMinimum = source.DurationMinimum,
        DurationMaximum = source.DurationMaximum,
    }
end

local function configuration(state)
    if type(state.policyConfig) == "table" then
        return state.policyConfig
    end

    local source = SandboxVars
        and SandboxVars.TGSRRHelicopterSchedule or nil
    if not source and SandboxVars then
        local sourceError
        source, sourceError = registeredSource(
            SandboxVars.TGSRRHelicopter)
        if not source then
            return nil, sourceError
                or "helicopter_schedule_missing"
        end
    end
    local config, configError = normalize(source)
    if not config then return nil, configError end
    state.policyConfig = config
    return config
end

local function calendarYear(slot, startYear, startMonth)
    if slot.month >= startMonth then
        return startYear + slot.challengeYear - 1
    end
    return startYear + slot.challengeYear
end

local function slotStartDay(slot, year, startYear, startMonth, gameTime)
    -- Vanilla stores helicopterDay as a world-day offset. Preserve that
    -- behavior by anchoring each recurring month to the challenge's original
    -- start day-of-month, rather than treating the delay as a calendar date.
    if year == startYear and slot.month == startMonth then
        return 0
    end
    local startDay =
        math.floor(tonumber(gameTime:getStartDay()) or 0) + 1
    return HelicopterScheduler.dayForDate(
        year, slot.month, startDay, gameTime)
end

function BasicSchedule.chooseNext(state, gameTime)
    local config, configError = configuration(state)
    if not config then return nil, configError end
    if not config.enabled then return nil, "exhausted" end

    local startYear = math.floor(tonumber(gameTime:getStartYear()) or 0)
    local startMonth =
        math.floor(tonumber(gameTime:getStartMonth()) or 0) + 1
    local today = math.floor(tonumber(gameTime:getNightsSurvived()) or 0)
    local firstSlot = math.max(1,
        math.floor(tonumber(state.slotIndex) or 0) + 1)

    for slotIndex = firstSlot, #config.slots do
        local slot = config.slots[slotIndex]
        local year = calendarYear(
            slot, startYear, startMonth)
        local slotDay, dateError = slotStartDay(
            slot, year, startYear, startMonth, gameTime)
        if not slotDay then return nil, dateError end

        -- DayMaximum is intentionally exclusive, matching vanilla's
        -- Rand.Next(6, 10), which produces world-day delays 6 through 9.
        local scheduledDay = slotDay + ZombRand(
            config.dayMinimum, config.dayMaximum)
        if scheduledDay > today then
            local date, resolvedDateError =
                HelicopterScheduler.dateForDay(scheduledDay, gameTime)
            if not date then return nil, resolvedDateError end
            local startHour = ZombRand(
                config.startHourMinimum,
                config.startHourMaximum + 1)
            local endHour = math.min(
                startHour + ZombRand(
                    config.durationMinimum,
                    config.durationMaximum + 1),
                24)
            return {
                slotIndex = slotIndex,
                challengeYear = slot.challengeYear,
                calendarYear = date.year,
                month = date.month,
                calendarDay = date.day,
                day = scheduledDay,
                startHour = startHour,
                endHour = endHour,
            }
        end
    end

    return nil, "exhausted"
end

function BasicSchedule.prepare(state)
    return configuration(state)
end

function BasicSchedule.isEnabledInSandbox()
    local source = SandboxVars
        and SandboxVars.TGSRRHelicopter or nil
    return type(source) == "table"
        and source.Enabled == true
end

function BasicSchedule.monthsForYear(challengeYear, state)
    state = state or {}
    local config = configuration(state)
    if not config then return {} end
    local source = config.monthsByYear[
        math.floor(tonumber(challengeYear) or 0)]
    if not source then return {} end

    local result = {}
    for index = 1, #source do result[index] = source[index] end
    return result
end

function BasicSchedule.normalize(source)
    return normalize(source)
end

function BasicSchedule.fromRegistered(source)
    local converted, convertError = registeredSource(source)
    if not converted then return nil, convertError end
    return normalize(converted)
end

return BasicSchedule
