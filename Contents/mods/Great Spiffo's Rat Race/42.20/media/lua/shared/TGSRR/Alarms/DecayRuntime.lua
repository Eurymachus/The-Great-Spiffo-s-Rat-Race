local Runtime = {}

local MOD_DATA_KEY = "TGSRR_AlarmDecay"
local SCHEMA_VERSION = 1

local function authoritative()
    return not (isClient and isClient())
end

local function integer(value, fallback)
    return math.floor(tonumber(value) or fallback or 0)
end

local function configuration()
    local options = SandboxVars and SandboxVars.TGSRRAlarmDecay or nil
    local minimum = math.max(0, integer(options and options.MinimumDay, 0))
    local maximum = math.max(0, integer(options and options.MaximumDay, 730))
    if maximum < minimum then minimum, maximum = maximum, minimum end

    return {
        enabled = options ~= nil and options.Enabled == true,
        minimum = minimum,
        maximum = maximum,
    }
end

local function randomInclusive(minimum, maximum)
    if maximum <= minimum then return minimum end
    return ZombRand(minimum, maximum + 1)
end

local function vanillaDecay()
    local sandboxOptions = getSandboxOptions and getSandboxOptions() or nil
    local setting = SandboxVars and SandboxVars.AlarmDecay or 2
    if sandboxOptions and sandboxOptions.randomAlarmDecay then
        return sandboxOptions:randomAlarmDecay(integer(setting, 2))
    end
    return randomInclusive(0, 30)
end

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
        data.overrideApplied = false
        data.minimum = nil
        data.maximum = nil
    end
    return data
end

local function forEachBuilding(callback)
    local world = getWorld and getWorld() or nil
    local metaGrid = world and world:getMetaGrid() or nil
    local buildings = metaGrid and metaGrid:getBuildings() or nil
    if not buildings then return 0 end

    local count = 0
    for i = 0, buildings:size() - 1 do
        local building = buildings:get(i)
        if building then
            callback(building)
            count = count + 1
        end
    end
    return count
end

function Runtime.apply()
    if not authoritative() then return false, "not_authoritative" end

    local config = configuration()
    local data = root()
    local changed = data.overrideApplied ~= config.enabled
        or (config.enabled and (data.minimum ~= config.minimum
            or data.maximum ~= config.maximum))
    if not changed then return false, "unchanged" end

    local count
    if config.enabled then
        count = forEachBuilding(function(building)
            building.alarmDecay =
                randomInclusive(config.minimum, config.maximum)
        end)
        data.overrideApplied = true
        data.minimum = config.minimum
        data.maximum = config.maximum
        print("[TGSRR Alarms] Applied custom alarm battery decay to "
            .. tostring(count) .. " buildings: "
            .. tostring(config.minimum) .. "-" .. tostring(config.maximum)
            .. " days after power shutoff.")
    else
        count = forEachBuilding(function(building)
            building.alarmDecay = vanillaDecay()
        end)
        data.overrideApplied = false
        data.minimum = nil
        data.maximum = nil
        print("[TGSRR Alarms] Restored vanilla alarm battery decay for "
            .. tostring(count) .. " buildings.")
    end

    data.updatedAtWorldAgeHours = getGameTime()
        and getGameTime():getWorldAgeHours() or nil
    return true, count
end

Runtime.configuration = configuration
Events.OnLoadedMapZones.Add(Runtime.apply)

return Runtime
