local EventTypes = {}

local registered = {
    ["session.started"] = true,
    ["day.started"] = true,
    ["outpost.deliverable.completed"] = true,
    ["outpost.completed"] = true,
    ["kills.milestone.reached"] = true,
    ["skill.level.reached"] = true,
    ["skill.milestone.reached"] = true,
    ["location.visited"] = true,
    ["town.visited"] = true,
    ["literature.baseline"] = true,
    ["literature.read"] = true,
    ["run.classification.changed"] = true,
    ["run.recovery.decided"] = true,
}

local function validName(name)
    if type(name) ~= "string" or not name:find(".", 1, true) then return false end
    local rebuilt = {}
    for segment in name:gmatch("[^.]+") do
        if not segment:match("^[a-z][a-z0-9_]*$") then return false end
        rebuilt[#rebuilt + 1] = segment
    end
    return #rebuilt >= 2 and table.concat(rebuilt, ".") == name
end

function EventTypes.register(name)
    if not validName(name) then return false, "invalid_event_type" end
    registered[name] = true
    return true
end

function EventTypes.isRegistered(name)
    return registered[name] == true
end

function EventTypes.all()
    local result = {}
    for name, _ in pairs(registered) do result[#result + 1] = name end
    table.sort(result)
    return result
end

return EventTypes
