TGSRR = TGSRR or {}

local Tracker = TGSRR.ChallengeTracker or {}
TGSRR.ChallengeTracker = Tracker

Tracker._modules = Tracker._modules or {}
Tracker._ordered = Tracker._ordered or {}

local function sortModules()
    table.sort(Tracker._ordered, function(a, b)
        if (a.order == b.order) then return a.id < b.id end
        return a.order < b.order
    end)
end

function Tracker.registerModule(module)
    if type(module) ~= "table" then error("TGSRR.ChallengeTracker.registerModule: module is required", 2) end
    if type(module.id) ~= "string" or module.id == "" then error("TGSRR.ChallengeTracker.registerModule: id is required", 2) end
    if type(module.title) ~= "string" or module.title == "" then error("TGSRR.ChallengeTracker.registerModule: title is required", 2) end
    if type(module.createView) ~= "function" then error("TGSRR.ChallengeTracker.registerModule: createView is required", 2) end
    if Tracker._modules[module.id] then error("TGSRR.ChallengeTracker.registerModule: duplicate id " .. module.id, 2) end

    module.order = tonumber(module.order) or 100
    Tracker._modules[module.id] = module
    Tracker._ordered[#Tracker._ordered + 1] = module
    sortModules()
    return module
end

function Tracker.getModule(id)
    return Tracker._modules[id]
end

function Tracker.getModules()
    local result = {}
    for i, module in ipairs(Tracker._ordered) do result[i] = module end
    return result
end

return Tracker
