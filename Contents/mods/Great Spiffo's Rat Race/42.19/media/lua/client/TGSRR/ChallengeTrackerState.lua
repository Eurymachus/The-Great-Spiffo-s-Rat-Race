local State = {}
local FILENAME = "TGSRR/ChallengeTrackerWindow.ini"

function State.load()
    local result = {}
    local reader = getFileReader(FILENAME, false)
    if not reader then return result end
    local line = reader:readLine()
    while line do
        local key, value = line:match("^([^=]+)=(.*)$")
        if key then result[key] = value end
        line = reader:readLine()
    end
    reader:close()
    return result
end

function State.save(window, launcher, isOpen)
    local values = State.load()
    if window then
        values.x = math.floor(window:getX())
        values.y = math.floor(window:getY())
        values.width = math.floor(window:getWidth())
        values.height = math.floor(window:getHeight())
        values.tab = window.activeModuleId or ""
    end
    if launcher then
        values.launcherX = math.floor(launcher:getX())
        values.launcherY = math.floor(launcher:getY())
    end
    if isOpen ~= nil then
        values.open = isOpen and "true" or "false"
    end

    local writer = getFileWriter(FILENAME, true, false)
    if not writer then return end
    writer:write("x=" .. tostring(values.x or "") .. "\n")
    writer:write("y=" .. tostring(values.y or "") .. "\n")
    writer:write("width=" .. tostring(values.width or "") .. "\n")
    writer:write("height=" .. tostring(values.height or "") .. "\n")
    writer:write("tab=" .. tostring(values.tab or "") .. "\n")
    writer:write("launcherX=" .. tostring(values.launcherX or "") .. "\n")
    writer:write("launcherY=" .. tostring(values.launcherY or "") .. "\n")
    writer:write("open=" .. tostring(values.open or "false") .. "\n")
    writer:close()
end

return State
