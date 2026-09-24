local OutpostSurveyIO = {}

local FILENAME = "TGSRR/Outposts.ini"
local WINDOW_STATE_FILENAME = "TGSRR/OutpostSurveyWindow.ini"

local function trim(value)
    if value == nil then return nil end
    return tostring(value):gsub("^%s+", ""):gsub("%s+$", "")
end

local function parseValue(value)
    local text = trim(value)
    if text == "true" then return true end
    if text == "false" then return false end
    local number = tonumber(text)
    return number ~= nil and number or text
end

local function sortedKeys(values)
    local keys = {}
    for key, _ in pairs(values) do
        keys[#keys + 1] = key
    end
    table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
    return keys
end

function OutpostSurveyIO.loadAll()
    local reader = getFileReader(FILENAME, false)
    if not reader then return {} end

    local sections = {}
    local current = nil
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local text = trim(line)
        if text ~= "" and text:sub(1, 1) ~= ";" and text:sub(1, 1) ~= "#" then
            local sectionName = text:match("^%[(.-)%]$")
            if sectionName then
                current = trim(sectionName)
                sections[current] = sections[current] or {}
            elseif current then
                local key, value = text:match("^(.-)=(.*)$")
                key = trim(key)
                if key and key ~= "" then
                    -- Java building/room IDs exceed Lua's exact integer range.
                    -- Keep every *Id field as text so repeated reads never round it.
                    if key:match("Id$") then
                        sections[current][key] = trim(value)
                    else
                        sections[current][key] = parseValue(value)
                    end
                end
            end
        end
    end
    reader:close()
    return sections
end

function OutpostSurveyIO.saveSection(sectionName, row, keyOrder)
    local sections = OutpostSurveyIO.loadAll()
    sections[sectionName] = row

    local writer = getFileWriter(FILENAME, true, false)
    if not writer then return false end

    for _, name in ipairs(sortedKeys(sections)) do
        writer:write("[" .. tostring(name) .. "]\n")
        local values = sections[name]
        local written = {}
        for _, key in ipairs(keyOrder or {}) do
            if values[key] ~= nil then
                writer:write(tostring(key) .. "=" .. tostring(values[key]) .. "\n")
                written[key] = true
            end
        end
        for _, key in ipairs(sortedKeys(values)) do
            if not written[key] and values[key] ~= nil then
                writer:write(tostring(key) .. "=" .. tostring(values[key]) .. "\n")
            end
        end
        writer:write("\n")
    end
    writer:close()
    return true
end

function OutpostSurveyIO.getFilename()
    return FILENAME
end

function OutpostSurveyIO.loadWindowPosition()
    local reader = getFileReader(WINDOW_STATE_FILENAME, false)
    if not reader then return nil, nil end
    local x, y = nil, nil
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local key, value = line:match("^%s*(.-)%s*=%s*(.-)%s*$")
        if key == "x" then x = tonumber(value) end
        if key == "y" then y = tonumber(value) end
    end
    reader:close()
    return x, y
end

function OutpostSurveyIO.saveWindowPosition(x, y)
    local writer = getFileWriter(WINDOW_STATE_FILENAME, true, false)
    if not writer then return false end
    writer:write("[Window]\n")
    writer:write("x=" .. tostring(math.floor(x)) .. "\n")
    writer:write("y=" .. tostring(math.floor(y)) .. "\n")
    writer:close()
    return true
end

return OutpostSurveyIO
