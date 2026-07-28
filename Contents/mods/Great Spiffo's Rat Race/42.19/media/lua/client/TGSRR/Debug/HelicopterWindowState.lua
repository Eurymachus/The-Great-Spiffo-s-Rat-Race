local State = {}

local FILENAME = "TGSRR/HelicopterDebugWindow.ini"
local values = nil

local function load()
    if values then return values end
    values = {}

    local reader = getFileReader(FILENAME, false)
    if not reader then return values end
    local line = reader:readLine()
    while line do
        local key, value = line:match("^([^=]+)=(.*)$")
        if key then values[key] = value end
        line = reader:readLine()
    end
    reader:close()
    return values
end

local function write()
    local writer = getFileWriter(FILENAME, true, false)
    if not writer then return false end
    local state = load()
    writer:write("x=" .. tostring(state.x or "") .. "\n")
    writer:write("y=" .. tostring(state.y or "") .. "\n")
    writer:write("open=" .. tostring(state.open or "false") .. "\n")
    writer:close()
    return true
end

function State.position(defaultX, defaultY)
    local state = load()
    return tonumber(state.x) or defaultX,
        tonumber(state.y) or defaultY
end

function State.isOpen()
    return load().open == "true"
end

function State.save(window, isOpen)
    local state = load()
    if window then
        state.x = tostring(math.floor(window:getX()))
        state.y = tostring(math.floor(window:getY()))
    end
    if isOpen ~= nil then
        state.open = isOpen and "true" or "false"
    end
    return write()
end

return State
