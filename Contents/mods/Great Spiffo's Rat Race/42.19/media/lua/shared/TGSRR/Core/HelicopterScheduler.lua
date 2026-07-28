local HelicopterScheduler = {}

local SCHEMA_VERSION = 1

local function integer(value, fallback)
    value = tonumber(value)
    if value == nil then return fallback end
    return math.floor(value)
end

local function stateFor(key)
    local state = ModData.getOrCreate(key)
    if state.schemaVersion ~= SCHEMA_VERSION then
        state.schemaVersion = SCHEMA_VERSION
        state.initialized = false
        state.exhausted = false
        state.policyId = nil
        state.slotIndex = nil
        state.current = nil
        state.initialVanilla = nil
    end
    return state
end

function HelicopterScheduler.read(gameTime)
    gameTime = gameTime or getGameTime()
    if not gameTime then return nil end

    return {
        today = integer(gameTime:getNightsSurvived(), 0),
        day = integer(gameTime:getHelicopterDay(), 0),
        startHour = integer(gameTime:getHelicopterStartHour(), 0),
        endHour = integer(gameTime:getHelicopterEndHour(), 0),
    }
end

function HelicopterScheduler.set(day, startHour, endHour, gameTime)
    gameTime = gameTime or getGameTime()
    if not gameTime then return nil, "game_time_unavailable" end

    day = integer(day, -1)
    startHour = integer(startHour, -1)
    endHour = integer(endHour, -1)

    if day < 0 then return nil, "invalid_day" end
    if startHour < 0 or startHour > 23 then
        return nil, "invalid_start_hour"
    end
    if endHour <= startHour or endHour > 24 then
        return nil, "invalid_end_hour"
    end

    gameTime:setHelicopterDay(day)
    gameTime:setHelicopterStartHour(startHour)
    gameTime:setHelicopterEndHour(endHour)
    return HelicopterScheduler.read(gameTime)
end

function HelicopterScheduler.clear(gameTime)
    gameTime = gameTime or getGameTime()
    if not gameTime then return nil, "game_time_unavailable" end

    gameTime:setHelicopterDay(0)
    gameTime:setHelicopterStartHour(0)
    gameTime:setHelicopterEndHour(0)
    return HelicopterScheduler.read(gameTime)
end

function HelicopterScheduler.dayForDate(year, month, day, gameTime)
    gameTime = gameTime or getGameTime()
    if not gameTime then return nil, "game_time_unavailable" end

    year = integer(year, -1)
    month = integer(month, -1)
    day = integer(day, -1)

    local startYear = integer(gameTime:getStartYear(), -1)
    local startMonth = integer(gameTime:getStartMonth(), -1)
    local startDay = integer(gameTime:getStartDay(), -1)
    if startYear < 0 or startMonth < 0 or startDay < 0 then
        return nil, "invalid_start_date"
    end
    if year < startYear or month < 1 or month > 12 or day < 1 then
        return nil, "invalid_target_date"
    end

    local targetMonth = month - 1
    local targetDay = day - 1
    local targetMonthDays = gameTime:daysInMonth(year, targetMonth)
    if targetDay >= targetMonthDays then
        return nil, "invalid_target_date"
    end

    local elapsed
    if year == startYear then
        elapsed = 0
        for currentMonth = startMonth, targetMonth - 1 do
            elapsed = elapsed
                + gameTime:daysInMonth(year, currentMonth)
        end
        elapsed = elapsed + targetDay - startDay
    else
        elapsed = -startDay
        for currentMonth = startMonth, 11 do
            elapsed = elapsed
                + gameTime:daysInMonth(startYear, currentMonth)
        end
        for currentYear = startYear + 1, year - 1 do
            for currentMonth = 0, 11 do
                elapsed = elapsed
                    + gameTime:daysInMonth(currentYear, currentMonth)
            end
        end
        for currentMonth = 0, targetMonth - 1 do
            elapsed = elapsed
                + gameTime:daysInMonth(year, currentMonth)
        end
        elapsed = elapsed + targetDay
    end

    return elapsed
end

function HelicopterScheduler.dateForDay(day, gameTime)
    gameTime = gameTime or getGameTime()
    if not gameTime then return nil, "game_time_unavailable" end

    day = integer(day, -1)
    if day < 0 then return nil, "invalid_day" end

    local year = integer(gameTime:getStartYear(), -1)
    local month = integer(gameTime:getStartMonth(), -1)
    local calendarDay = integer(gameTime:getStartDay(), -1)
    if year < 0 or month < 0 or calendarDay < 0 then
        return nil, "invalid_start_date"
    end

    local remaining = day
    while remaining > 0 do
        local available = gameTime:daysInMonth(year, month)
            - calendarDay - 1
        if remaining <= available then
            calendarDay = calendarDay + remaining
            remaining = 0
        else
            remaining = remaining - available - 1
            calendarDay = 0
            month = month + 1
            if month >= 12 then
                month = 0
                year = year + 1
            end
        end
    end

    return {
        year = year,
        month = month + 1,
        day = calendarDay + 1,
    }
end

local function initializeState(state, policy, schedule)
    state.initialized = true
    state.exhausted = false
    state.policyId = policy.id
    state.slotIndex = 0
    state.current = nil
    state.initialVanilla = {
        day = schedule.day,
        startHour = schedule.startHour,
        endHour = schedule.endHour,
    }
end

function HelicopterScheduler.update(options)
    options = options or {}
    local policy = options.policy
    if type(policy) ~= "table"
            or type(policy.chooseNext) ~= "function" then
        return nil, "invalid_policy"
    end

    local key = tostring(options.modDataKey or "TGSRR_HelicopterScheduler")
    local gameTime = options.gameTime or getGameTime()
    if not gameTime then return nil, "game_time_unavailable" end

    local state = stateFor(key)
    local schedule = HelicopterScheduler.read(gameTime)
    local replacedInitialSchedule = false
    if not state.initialized or state.policyId ~= policy.id then
        initializeState(state, policy, schedule)
        if options.replaceScheduleOnInitialize == true then
            HelicopterScheduler.clear(gameTime)
            replacedInitialSchedule = true
        end
    end
    if type(policy.prepare) == "function" then
        local prepared, prepareError = policy.prepare(state, gameTime)
        if not prepared then return nil, prepareError end
    end

    if state.exhausted then return state, "exhausted" end
    if not replacedInitialSchedule
            and schedule.day >= schedule.today then
        return state, "scheduled"
    end

    local proposed, reason = policy.chooseNext(state, gameTime)
    if not proposed then
        if reason == "exhausted" then state.exhausted = true end
        return state, reason or "no_schedule"
    end

    local applied, setError = HelicopterScheduler.set(
        proposed.day,
        proposed.startHour,
        proposed.endHour,
        gameTime
    )
    if not applied then return nil, setError end

    state.slotIndex = proposed.slotIndex
    state.current = {
        slotIndex = proposed.slotIndex,
        challengeYear = proposed.challengeYear,
        calendarYear = proposed.calendarYear,
        month = proposed.month,
        calendarDay = proposed.calendarDay,
        day = proposed.day,
        startHour = proposed.startHour,
        endHour = proposed.endHour,
    }

    print(string.format(
        "[TGSRR] Scheduled helicopter: challenge year %d, %04d-%02d-%02d, %02d:00-%02d:00",
        proposed.challengeYear,
        proposed.calendarYear,
        proposed.month,
        proposed.calendarDay,
        proposed.startHour,
        proposed.endHour
    ))
    return state, "scheduled_new"
end

return HelicopterScheduler
