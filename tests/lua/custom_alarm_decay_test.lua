local failures = 0

package.loaded["TGSRR/Challenge/Context"] = {
    isActive = function() return true end,
}

local function expect(label, actual, expected)
    if actual ~= expected then
        io.stderr:write(label .. ": expected " .. tostring(expected)
            .. ", got " .. tostring(actual) .. "\n")
        failures = failures + 1
    end
end

SandboxVars = {
    ElecShutModifier = 14,
    TGSRRAlarmDecay = {
        Enabled = true,
        MinimumDay = 5,
        MaximumDay = 10,
    },
}

ZombRand = function(minimum, maximum)
    expect("inclusive random lower", minimum, 5)
    expect("inclusive random upper", maximum, 11)
    return 7
end

local alarmData = {}
ModData = {
    getOrCreate = function()
        return alarmData
    end,
}

local playerUpdateHandler
local gameStartHandlers = {}
local tickHandler
Events = {
    OnLoadedMapZones = { Add = function() end },
    OnNewGame = { Add = function() end },
    OnGameStart = { Add = function(handler)
        gameStartHandlers[#gameStartHandlers + 1] = handler
    end },
    OnPlayerUpdate = { Add = function(handler) playerUpdateHandler = handler end },
    LoadChunk = { Add = function() end },
    OnSeeNewRoom = { Add = function() end },
    OnTick = { Add = function(handler) tickHandler = handler end },
}

local runtimePath = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
    .. "shared/TGSRR/Alarms/CustomDecayRuntime.lua"
local Runtime = dofile(runtimePath)

local config = Runtime.configuration()
expect("enabled", config.enabled, true)
expect("minimum", config.minimum, 5)
expect("maximum", config.maximum, 10)
expect("expiry includes power shutoff", Runtime.expiryDay(14, 5, 10), 21)
expect("live on expiry day",
    Runtime.isLive({ expiryDay = 21, triggered = false }, 21), true)
expect("expired after expiry day",
    Runtime.isLive({ expiryDay = 21, triggered = false }, 21.01), false)
expect("triggered cannot fire",
    Runtime.isLive({ expiryDay = 21, triggered = true }, 20), false)

local claimedAlarmed = true
local claimedDefinition = {
    getIDString = function() return "claimed-building" end,
    isFullyStreamedIn = function() return true end,
    isAlarmed = function() return claimedAlarmed end,
    setAlarmed = function(_, value) claimedAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 100 end,
            getY = function() return 200 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 100 end,
    getY = function() return 200 end,
}
local claimedSquare = {
    getX = function() return 96 end,
    getY = function() return 200 end,
    getBuilding = function()
        return { getDef = function() return claimedDefinition end }
    end,
}
local initialMetaBuildings = {
    size = function() return 1 end,
    get = function() return claimedDefinition end,
}
getWorld = function()
    return {
        getMetaGrid = function()
            return { getBuildings = function() return initialMetaBuildings end }
        end,
    }
end
expect("world snapshot succeeds", Runtime.capture(), true)
expect("successful vanilla roll snapshotted",
    alarmData.buildings["claimed-building"].pending, true)
expect("snapshot leaves vanilla alarm armed", claimedAlarmed, true)
expect("pending snapshot stores expiry",
    alarmData.buildings["claimed-building"].expiryDay, 21)
local claimedChunk = {
    getMinLevel = function() return 0 end,
    getMaxLevel = function() return 0 end,
    getGridSquare = function(_, x, y)
        if x == 0 and y == 0 then return claimedSquare end
        return nil
    end,
}
expect("chunk capture succeeds", Runtime.onLoadChunk(claimedChunk), true)
expect("surviving alarm claimed", claimedAlarmed, false)
expect("claimed record stored",
    alarmData.buildings["claimed-building"] ~= nil, true)

local claimedIsoBuilding = {
    getDef = function() return claimedDefinition end,
}
local function javaList(values)
    return {
        size = function() return #values end,
        get = function(_, index) return values[index + 1] end,
    }
end
instanceof = function(object, className)
    return className == "IsoZombie" and object and object.zombie == true
end
local claimedRoomZombieCount = 0
local claimedRoom = {
    getBuilding = function() return claimedIsoBuilding end,
    getSquares = function()
        local zombies = {}
        for i = 1, claimedRoomZombieCount do zombies[i] = { zombie = true } end
        return javaList({
            { getMovingObjects = function() return javaList(zombies) end },
        })
    end,
}
Runtime.onSeeNewRoom(claimedRoom)
expect("room check keeps vanilla path disabled", claimedAlarmed, false)
-- Simulate VirtualZombieManager.roomSpotted() spawning indoor zombies.
claimedRoomZombieCount = 1
Runtime.reconcileRoomNullifiers()
expect("room population removes custom record",
    alarmData.buildings["claimed-building"], nil)

alarmData.buildings["claimed-building"] = {
    expiryDay = 21,
    triggered = false,
}
claimedAlarmed = false
claimedRoomZombieCount = 0
Runtime.onSeeNewRoom(claimedRoom)
expect("second room check keeps vanilla path disabled", claimedAlarmed, false)
-- No new room zombie means vanilla would leave the alarm intact.
Runtime.reconcileRoomNullifiers()
expect("surviving room alarm reclaimed", claimedAlarmed, false)
expect("surviving room record retained",
    alarmData.buildings["claimed-building"] ~= nil, true)

local partialAlarmed = true
local partialDefinition = {
    getIDString = function() return "partial-building" end,
    isFullyStreamedIn = function() return false end,
    isAlarmed = function() return partialAlarmed end,
    setAlarmed = function(_, value) partialAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 250 end,
            getY = function() return 350 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 250 end,
    getY = function() return 350 end,
}
alarmData.buildings["partial-building"] = {
    pending = true,
    triggered = false,
    x = 250,
    y = 350,
    z = 0,
}
local partialRoom = {
    getBuilding = function()
        return { getDef = function() return partialDefinition end }
    end,
    getSquares = function()
        return javaList({
            { getMovingObjects = function() return javaList({}) end },
        })
    end,
}
Runtime.onSeeNewRoom(partialRoom)
Runtime.reconcileRoomNullifiers()
expect("room callback does not claim partial building", partialAlarmed, true)
expect("room callback leaves partial record pending",
    alarmData.buildings["partial-building"].pending, true)

local ghostAlarmed = true
local ghostDefinition = {
    getIDString = function() return "ghost-building" end,
    isFullyStreamedIn = function() return false end,
    isAlarmed = function() return ghostAlarmed end,
    setAlarmed = function(_, value) ghostAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 650 end,
            getY = function() return 750 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 650 end,
    getY = function() return 750 end,
}
alarmData.buildings["ghost-building"] = {
    pending = true,
    triggered = false,
    expiryDay = 21,
    x = 650,
    y = 750,
    z = 0,
}
local ghostIsoBuilding = {
    getDef = function() return ghostDefinition end,
}
local ghostPlayer = {
    getCurrentSquare = function()
        return {
            getRoom = function() return nil end,
            getBuilding = function() return ghostIsoBuilding end,
        }
    end,
    isInvisible = function() return true end,
    isGhostMode = function() return true end,
}
playerUpdateHandler(ghostPlayer)
expect("player update does not claim pending building", ghostAlarmed, true)
expect("player update leaves record pending",
    alarmData.buildings["ghost-building"].pending, true)
expect("ghost player does not trigger alarm",
    alarmData.buildings["ghost-building"].triggered, false)

local nullifiedPartialAlarmed = true
local nullifiedPartialDefinition = {
    getIDString = function() return "partial-nullified" end,
    isAlarmed = function() return nullifiedPartialAlarmed end,
    setAlarmed = function(_, value) nullifiedPartialAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 450 end,
            getY = function() return 550 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 450 end,
    getY = function() return 550 end,
}
alarmData.buildings["partial-nullified"] = {
    pending = true,
    triggered = false,
}
local nullifiedPartialRoom = {
    getBuilding = function()
        return { getDef = function() return nullifiedPartialDefinition end }
    end,
}
local nullifiedRoomZombieCount = 0
nullifiedPartialRoom.getSquares = function()
    local zombies = {}
    for i = 1, nullifiedRoomZombieCount do
        zombies[i] = { zombie = true }
    end
    return javaList({
        { getMovingObjects = function() return javaList(zombies) end },
    })
end
Runtime.onSeeNewRoom(nullifiedPartialRoom)
-- Simulate roomSpotted() successfully placing indoor zombies.
nullifiedRoomZombieCount = 1
Runtime.reconcileRoomNullifiers()
expect("room callback leaves nullified candidate for LoadChunk",
    alarmData.buildings["partial-nullified"].pending, true)

local pendingAlarmed = true
local pendingFullyStreamed = false
local pendingDefinition = {
    getIDString = function() return "pending-building" end,
    isFullyStreamedIn = function() return pendingFullyStreamed end,
    isAlarmed = function() return pendingAlarmed end,
    setAlarmed = function(_, value) pendingAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 300 end,
            getY = function() return 400 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 300 end,
    getY = function() return 400 end,
}
local metaBuildings = {
    size = function() return 2 end,
    get = function(_, index)
        if index == 0 then return claimedDefinition end
        return pendingDefinition
    end,
}
local debugMetaGrid = {
    getBuildings = function() return metaBuildings end,
}
getWorld = function()
    return {
        getMetaGrid = function()
            return debugMetaGrid
        end,
    }
end
Runtime.capture()
local debugRecords = Runtime.listDebugRecords()
expect("debug list includes owned and pending", #debugRecords, 5)
expect("pending candidate sorted first", debugRecords[1].pending, true)
local foundPendingBuilding = false
for _, record in ipairs(debugRecords) do
    if record.key == "pending-building" and record.pending == true then
        foundPendingBuilding = true
    end
end
expect("pending candidate identified", foundPendingBuilding, true)

ArrayList = {
    new = function()
        local values = {}
        return {
            add = function(_, value) values[#values + 1] = value end,
            size = function() return #values end,
            get = function(_, index) return values[index + 1] end,
        }
    end,
}
debugMetaGrid.getBuildingsIntersecting = function(_, x, y, w, h, buildings)
    expect("expanded lookup x", x, 399)
    expect("expanded lookup y", y, 799)
    expect("expanded lookup width", w, 10)
    expect("expanded lookup height", h, 10)
    buildings:add(pendingDefinition)
end
local borderSquare = {
    getX = function() return 400 end,
    getY = function() return 800 end,
    getBuilding = function() return nil end,
}
local borderChunk = {
    wx = 50,
    wy = 100,
    getMinLevel = function() return 0 end,
    getMaxLevel = function() return 0 end,
    getGridSquare = function(_, x, y)
        if x == 0 and y == 0 then return borderSquare end
        return nil
    end,
}
pendingAlarmed = false
Runtime.onLoadChunk(borderChunk)
expect("partial false alarm state is not treated as final", pendingAlarmed, false)
expect("border-only partial record remains pending",
    alarmData.buildings["pending-building"].pending, true)
Runtime.processPendingChunkClaims()
expect("deferred validation waits for full streaming", pendingAlarmed, false)
pendingAlarmed = true
pendingFullyStreamed = true
Runtime.processPendingChunkClaims()
expect("deferred LoadChunk building finalized", pendingAlarmed, false)
expect("deferred LoadChunk record owned",
    alarmData.buildings["pending-building"].pending, false)

local lateAlarmed = true
local lateDefinition = {
    getIDString = function() return "late-building" end,
    isFullyStreamedIn = function() return true end,
    isAlarmed = function() return lateAlarmed end,
    setAlarmed = function(_, value) lateAlarmed = value end,
    getFirstRoom = function()
        return {
            getX = function() return 480 end,
            getY = function() return 880 end,
            getZ = function() return 0 end,
        }
    end,
    getX = function() return 480 end,
    getY = function() return 880 end,
}
alarmData.buildings["late-building"] = {
    pending = true,
    triggered = false,
    expiryDay = 21,
    x = 480,
    y = 880,
    z = 0,
}
local lateSquareAvailable = false
local lateSquare = {
    getX = function() return 480 end,
    getY = function() return 880 end,
    getBuilding = function()
        return { getDef = function() return lateDefinition end }
    end,
}
local lateChunk = {
    wx = 60,
    wy = 110,
    getMinLevel = function() return 0 end,
    getMaxLevel = function() return 0 end,
    getGridSquare = function(_, x, y)
        if lateSquareAvailable and x == 0 and y == 0 then return lateSquare end
        return nil
    end,
}
debugMetaGrid.getBuildingsIntersecting = function() end
Runtime.onLoadChunk(lateChunk)
expect("initial LoadChunk can miss late squares",
    alarmData.buildings["late-building"].pending, true)
lateSquareAvailable = true
Runtime.processPendingChunkRescans()
expect("deferred chunk rescan discovers late BuildingDef",
    alarmData.buildings["late-building"].pending, false)
expect("late BuildingDef alarm claimed", lateAlarmed, false)

local spawnAlarmed = true
local spawnDefinition = {
    getIDString = function() return "spawn-building" end,
    setAlarmed = function(_, value) spawnAlarmed = value end,
}
local spawnSquare = {
    getBuilding = function()
        return {
            getDef = function() return spawnDefinition end,
        }
    end,
}
alarmData.schemaVersion = 1
alarmData.buildings = alarmData.buildings or {}
alarmData.buildings["spawn-building"] = {
    expiryDay = 21,
    triggered = false,
}
expect("spawn building cleared",
    Runtime.clearSpawnBuilding(nil, spawnSquare), true)
expect("spawn building disarmed", spawnAlarmed, false)
expect("spawn record removed",
    alarmData.buildings["spawn-building"], nil)

SandboxVars.TGSRRAlarmDecay.MinimumDay = 20
SandboxVars.TGSRRAlarmDecay.MaximumDay = 10
config = Runtime.configuration()
expect("reversed minimum normalized", config.minimum, 10)
expect("reversed maximum normalized", config.maximum, 20)

package.loaded["TimedActions/ISOpenCloseWindow"] = true
package.loaded["TimedActions/ISSmashWindow"] = true
ISOpenCloseWindow = { perform = function() end }
ISSmashWindow = { start = function() end }
isServer = function() return true end
gameStartHandlers[2]()

local vehicleWindow = {
    isDestroyed = function() return false end,
}
ISSmashWindow.start({
    window = vehicleWindow,
    vehiclePart = {},
    character = {},
})
local vehicleTickOk = pcall(tickHandler)
expect("vehicle window ignored by building alarm watcher", vehicleTickOk, true)

if failures > 0 then os.exit(1) end
print("custom_alarm_decay_test: ok")
