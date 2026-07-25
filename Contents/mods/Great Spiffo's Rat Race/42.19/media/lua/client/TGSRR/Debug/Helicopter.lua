TGSRR_Debug = TGSRR_Debug or {}
TGSRR_Debug.Helicopter = TGSRR_Debug.Helicopter or {}

local Helicopter = TGSRR_Debug.Helicopter

local function requireDebugMode()
    if isDebugEnabled() then return true end

    print("[TGSRR] Helicopter debug functions require debug mode.")
    return false
end

function Helicopter.getSchedule()
    if not requireDebugMode() then return nil end

    local gameTime = getGameTime()
    local schedule = {
        today = gameTime:getNightsSurvived(),
        day = gameTime:getHelicopterDay(),
        startHour = gameTime:getHelicopterStartHour(),
        endHour = gameTime:getHelicopterEndHour(),
    }

    print(string.format(
        "[TGSRR] Today=%d | Helicopter day=%d | Start=%d:00 | End=%d:00",
        schedule.today,
        schedule.day,
        schedule.startHour,
        schedule.endHour
    ))

    return schedule
end

function Helicopter.setSchedule(day, startHour, endHour)
    if not requireDebugMode() then return nil end

    day = math.floor(tonumber(day) or -1)
    startHour = math.floor(tonumber(startHour) or -1)
    endHour = math.floor(tonumber(endHour) or -1)

    if day < 0 then
        error("TGSRR helicopter day must be zero or greater")
    end
    if startHour < 0 or startHour > 24 then
        error("TGSRR helicopter start hour must be between 0 and 24")
    end
    if endHour < 0 or endHour > 24 then
        error("TGSRR helicopter end hour must be between 0 and 24")
    end
    if endHour <= startHour then
        error("TGSRR helicopter end hour must be later than its start hour")
    end

    local gameTime = getGameTime()
    gameTime:setHelicopterDay(day)
    gameTime:setHelicopterStartHour(startHour)
    gameTime:setHelicopterEndHour(endHour)

    print("[TGSRR] Helicopter schedule updated; reading it back...")
    return Helicopter.getSchedule()
end

