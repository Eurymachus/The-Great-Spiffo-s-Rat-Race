local ActiveGameplayClock = {}

function ActiveGameplayClock.milliseconds()
    if getTimestampMs then return tonumber(getTimestampMs()) end
    return nil
end

local function speedControls()
    if UIManager and UIManager.getSpeedControls then
        local ok, result = pcall(function()
            return UIManager.getSpeedControls()
        end)
        if ok and result then return result end
    end
    if type(getSpeedControls) == "function" then
        local ok, result = pcall(getSpeedControls)
        if ok and result then return result end
    end
    return nil
end

local function requestedSpeed()
    local globalSpeed = nil
    local uiSpeed = nil
    if type(getGameSpeed) == "function" then
        local ok, result = pcall(getGameSpeed)
        if ok and type(result) == "number" then
            globalSpeed = result
        end
    end
    local controls = speedControls()
    if controls and controls.getCurrentGameSpeed then
        local ok, result = pcall(function()
            return controls:getCurrentGameSpeed()
        end)
        if ok and type(result) == "number" then
            uiSpeed = result
        end
    end
    if globalSpeed ~= nil and uiSpeed ~= nil then
        if globalSpeed <= 0 or uiSpeed <= 0 then return 0 end
        return math.max(globalSpeed, uiSpeed)
    end
    if globalSpeed ~= nil then return globalSpeed end
    if uiSpeed ~= nil then return uiSpeed end
    return 1
end

local function pauseMenuVisible()
    if type(MainScreen) ~= "table" or not MainScreen.instance
            or MainScreen.instance.inGame ~= true then
        return false
    end
    local screen = MainScreen.instance
    if screen.getIsVisible then
        local ok, visible = pcall(function()
            return screen:getIsVisible()
        end)
        if ok and visible then return true end
    end
    if screen.isVisible then
        local ok, visible = pcall(function()
            return screen:isVisible()
        end)
        if ok and visible then return true end
    end
    return false
end

function ActiveGameplayClock.isPaused(player)
    if not player then return true end
    if pauseMenuVisible() then return true end
    if type(isGamePaused) == "function" then
        local ok, paused = pcall(isGamePaused)
        if ok and paused then return true end
    end
    return requestedSpeed() <= 0
end

return ActiveGameplayClock
