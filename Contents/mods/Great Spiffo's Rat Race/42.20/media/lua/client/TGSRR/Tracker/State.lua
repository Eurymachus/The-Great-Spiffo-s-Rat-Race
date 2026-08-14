local State = {}
local FILENAME = "TGSRR/ChallengeTrackerWindow.ini"
local KEY_ORDER = { "x", "y", "tab", "launcherX", "launcherY", "open" }
local values = nil
local dirty = false

function State.load()
    if values then return values end
    values = {}
    local reader = getFileReader(FILENAME, false)
    if not reader then return values end
    local line = reader:readLine()
    while line do
        local key, parsedValue = line:match("^([^=]+)=(.*)$")
        if key then values[key] = parsedValue end
        line = reader:readLine()
    end
    reader:close()
    return values
end

local function write(values)
    local writer = getFileWriter(FILENAME, true, false)
    if not writer then return false end
    local written = {}
    for _, key in ipairs(KEY_ORDER) do
        writer:write(key .. "=" .. tostring(values[key] or (key == "open" and "false" or "")) .. "\n")
        written[key] = true
    end
    local extraKeys = {}
    for key in pairs(values) do
        if not written[key] then extraKeys[#extraKeys + 1] = key end
    end
    table.sort(extraKeys)
    for _, key in ipairs(extraKeys) do
        writer:write(tostring(key) .. "=" .. tostring(values[key] or "") .. "\n")
    end
    writer:close()
    return true
end

function State.save(window, launcher, isOpen)
    local state = State.load()
    local changed = false
    local function set(key, value)
        value = tostring(value)
        if state[key] ~= value then
            state[key] = value
            changed = true
        end
    end
    if window then
        set("x", math.floor(window:getX()))
        set("y", math.floor(window:getY()))
        set("tab", window.activeModuleId or "")
        if state.width ~= nil or state.height ~= nil then
            state.width = nil
            state.height = nil
            changed = true
        end
    end
    if launcher then
        set("launcherX", math.floor(launcher:getX()))
        set("launcherY", math.floor(launcher:getY()))
    end
    if isOpen ~= nil then
        set("open", isOpen and "true" or "false")
    end
    if changed then dirty = true end
    return changed
end

function State.getValue(key, default)
    local value = State.load()[key]
    if value == nil then return default end
    return value
end

function State.setValue(key, value)
    if not key or key == "" then return false end
    local state = State.load()
    value = value == nil and "" or tostring(value)
    if state[key] == value then return false end
    state[key] = value
    dirty = true
    return true
end

function State.setValues(updates)
    if type(updates) ~= "table" then return false end
    local changed = false
    for key, value in pairs(updates) do
        if key and key ~= "" then changed = State.setValue(key, value) or changed end
    end
    return changed
end

function State.isDirty()
    return dirty
end

function State.flush()
    if not dirty then return false end
    if not write(State.load()) then return false end
    dirty = false
    return true
end

Events.OnSave.Add(State.flush)

return State
