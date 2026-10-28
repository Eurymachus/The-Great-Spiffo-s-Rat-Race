local OfficialMode = {}

OfficialMode.legacy = "The Great Spiffo's Rat Race"
OfficialMode.storage = "Challenges"
OfficialMode.prefix = "TGSRR_"

function OfficialMode.enabled()
    local core = getCore and getCore() or nil
    local version = core and core.getVersionNumber and core:getVersionNumber() or ""
    local minor = tostring(version):match("^42%.(%d+)")
    return minor ~= nil and tonumber(minor) >= 22
end

function OfficialMode.isSave(mode, name)
    return tostring(mode or "") == OfficialMode.storage
        and type(name) == "string"
        and name:sub(1, #OfficialMode.prefix) == OfficialMode.prefix
        and #name > #OfficialMode.prefix
end

function OfficialMode.isCurrent()
    local world = getWorld and getWorld() or nil
    return world and OfficialMode.isSave(world:getGameMode(), world:getWorld()) or false
end

return OfficialMode
