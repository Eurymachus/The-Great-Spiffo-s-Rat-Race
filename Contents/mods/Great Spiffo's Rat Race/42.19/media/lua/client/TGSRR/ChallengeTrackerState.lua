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

function State.save(window)
    local writer = getFileWriter(FILENAME, true, false)
    if not writer then return end
    writer:write("x=" .. tostring(math.floor(window:getX())) .. "\n")
    writer:write("y=" .. tostring(math.floor(window:getY())) .. "\n")
    writer:write("width=" .. tostring(math.floor(window:getWidth())) .. "\n")
    writer:write("height=" .. tostring(math.floor(window:getHeight())) .. "\n")
    writer:write("tab=" .. tostring(window.activeModuleId or "") .. "\n")
    writer:close()
end

return State
