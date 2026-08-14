local loadedMapZonesHandler = nil
local loadChunkHandler = nil

package.loaded["TGSRR/Challenge/Context"] = {
    isActive = function() return true end,
}

local populateRolls = 0
package.loaded["TGSRR/Animals/RanchSpawner"] = {
    ranchSpawnChance = function(setting)
        assert(setting == 3)
        return 6
    end,
    shouldPopulate = function(setting)
        assert(setting == 3)
        populateRolls = populateRolls + 1
        return false
    end,
    populate = function()
        error("populate must not run after a failed chance roll")
    end,
}
local mortalityEnabled = true
package.loaded["TGSRR/Animals/RanchMortality"] = {
    configuration = function()
        return { enabled = mortalityEnabled }
    end,
}

SandboxVars = { AnimalRanchChance = 3 }

Events = {
    OnLoadedMapZones = {
        Add = function(handler) loadedMapZonesHandler = handler end,
    },
    LoadChunk = {
        Add = function(handler) loadChunkHandler = handler end,
    },
}

function isClient() return false end

local worldAge = 120
function getGameTime()
    return {
        getWorldAgeHours = function() return worldAge end,
    }
end

local modData = {}
ModData = {
    getOrCreate = function(key)
        modData[key] = modData[key] or {}
        return modData[key]
    end,
}

local designationValues = {}
local function designationList()
    return {
        size = function() return #designationValues end,
        get = function(_, index) return designationValues[index + 1] end,
    }
end

DesignationZone = {
    getAllZonesByType = function(zoneType)
        assert(zoneType == "AnimalZone")
        return designationList()
    end,
}

local designationCreateCalls = 0
DesignationZoneAnimal = {
    new = function(name, x, y, z, x2, y2, doSync)
        designationCreateCalls = designationCreateCalls + 1
        assert(doSync == true)
        local value = {
            name = name,
            getName = function(self) return self.name end,
            setName = function(self, newName) self.name = newName end,
            getX = function() return x end,
            getY = function() return y end,
            getZ = function() return z end,
            getW = function() return x2 - x end,
            getH = function() return y2 - y end,
        }
        designationValues[#designationValues + 1] = value
        return value
    end,
}

local function zone(x)
    local state = {
        type = "Ranch",
        fullyStreamed = false,
    }
    local value = {
        getName = function() return "cow" end,
        getType = function() return state.type end,
        setType = function(_, valueType) state.type = valueType end,
        getX = function() return x end,
        getY = function() return 200 end,
        getZ = function() return 0 end,
        getWidth = function() return 20 end,
        getHeight = function() return 30 end,
        isFullyStreamed = function() return state.fullyStreamed end,
    }
    return value, state
end

local ranch, ranchState = zone(100)
local adjoiningRanch, adjoiningRanchState = zone(120)
local chunk = {
    getZonesSize = function() return 2 end,
    getZone = function(_, index)
        if index == 0 then return ranch end
        return adjoiningRanch
    end,
}
local cell = {
    hasChunk = function(_, x, y) return x == 0 and y == 0 end,
    getChunk = function() return chunk end,
}
local metaGrid = {
    getMinX = function() return 0 end,
    getMinY = function() return 0 end,
    getMaxX = function() return 0 end,
    getMaxY = function() return 0 end,
    getCellData = function() return cell end,
    getZonesIntersecting = function()
        error("whole-world intersection must not be used")
    end,
}
local world = {
    getMetaGrid = function() return metaGrid end,
}
function getWorld() return world end

local Runtime = require "TGSRR/Animals/RanchRuntime"

assert(loadedMapZonesHandler == Runtime.onLoadedMapZones)
assert(loadChunkHandler == Runtime.onLoadChunk)

loadedMapZonesHandler()
assert(ranchState.type == "TGSRR_Ranch")
assert(adjoiningRanchState.type == "TGSRR_Ranch")

local key = "100:200:0:20:30:cow"
local adjoiningKey = "120:200:0:20:30:cow"
local persisted = modData.TGSRR_RanchControl
assert(persisted.schemaVersion == 1)
assert(persisted.ranches[key].ready == false)
assert(persisted.ranches[key].interceptedAt == 120)

loadChunkHandler()
assert(persisted.ranches[key].ready == false)

worldAge = 124
ranchState.fullyStreamed = true
adjoiningRanchState.fullyStreamed = true
loadChunkHandler()
assert(persisted.ranches[key].ready == true)
assert(persisted.ranches[key].readyAt == 124)
assert(persisted.ranches[key].confirmedControlledType == true)
assert(persisted.ranches[key].designationAvailable == true)
assert(persisted.ranches[key].designationCreated == true)
assert(persisted.ranches[key].spawnProcessed == true)
assert(persisted.ranches[key].spawnChance == 6)
assert(persisted.ranches[key].spawnSkippedByChance == true)
assert(persisted.ranches[key].designationName == "Ranch")
assert(designationValues[1]:getName() == "Ranch")
assert(designationCreateCalls == 2)
assert(populateRolls == 1)
assert(persisted.ranches[adjoiningKey].ready == true)
assert(persisted.ranches[adjoiningKey].spawnProcessed == true)
assert(persisted.ranches[adjoiningKey].designationName == "Ranch")
assert(designationValues[2]:getName() == "Ranch")
local inheritedCount = 0
for _, record in pairs(persisted.ranches) do
    if record.spawnInheritedFrom then
        inheritedCount = inheritedCount + 1
    end
end
assert(inheritedCount == 1)

loadChunkHandler()
assert(designationCreateCalls == 2)
assert(populateRolls == 1)

function ZombRand(maximum)
    assert(maximum == 10000)
    return 4321
end
function getText(key, first, second)
    if key == "IGUI_AnimalType_Global_chicken" then return "Chicken" end
    if key == "UI_Ranch" then
        return "Ranch " .. first .. " " .. tostring(second)
    end
    error("unexpected translation key: " .. tostring(key))
end

local successfulDesignation = {
    name = "TGSRR Ranch (chicken)",
    getName = function(self) return self.name end,
    setName = function(self, name) self.name = name end,
}
local successfulRecord = {
    spawnProcessed = true,
    spawnedFemales = 4,
    spawnedMales = 1,
    spawnedBabies = 2,
    spawnDefinition = "chicken",
    spawnGlobalName = "chicken",
}
Runtime.updateDesignationName(successfulDesignation, successfulRecord)
assert(successfulDesignation:getName() == "Ranch Chicken 4321")
assert(successfulRecord.designationName == "Ranch Chicken 4321")
Runtime.updateDesignationName(successfulDesignation, successfulRecord)
assert(successfulDesignation:getName() == "Ranch Chicken 4321")

local connectedDesignation = {
    name = "Ranch",
    getName = function(self) return self.name end,
    setName = function(self, name) self.name = name end,
}
local connectedRecord = {
    spawnProcessed = true,
    spawnInheritedFrom = key,
    spawnedFemales = 0,
    spawnedMales = 0,
    spawnedBabies = 0,
    designationName = successfulRecord.designationName,
}
Runtime.updateDesignationName(connectedDesignation, connectedRecord)
assert(connectedDesignation:getName() == "Ranch Chicken 4321")

local status = Runtime.getStatus()
assert(status.initialized == true)
assert(status.ranches[key].zone == ranch)

mortalityEnabled = false
loadedMapZonesHandler()
assert(ranchState.type == "Ranch")
assert(adjoiningRanchState.type == "Ranch")
assert(Runtime.getStatus().initialized == false)

print("ranch runtime test passed")
