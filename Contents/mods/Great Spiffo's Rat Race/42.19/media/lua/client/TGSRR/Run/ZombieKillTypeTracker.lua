local ZombieKillTypeTracker = {}

local TAG_KEY = "TGSRR_FenceWindowKillAssist"
local TYPES = {
    "standing",
    "onfront",
    "onback",
    "fenceAssist",
    "windowAssist",
}

local activeRun = nil
local activePlayer = nil

local function variable(zombie, name)
    return zombie.getVariableBoolean
        and zombie:getVariableBoolean(name) == true
end

local function modData(zombie)
    return zombie and zombie.getModData and zombie:getModData() or nil
end

local function existingModData(zombie)
    if not zombie or not zombie.getModData then return nil end
    if zombie.hasModData and not zombie:hasModData() then return nil end
    return zombie:getModData()
end

local function traversalType(zombie)
    if variable(zombie, "ClimbFenceStarted")
            or variable(zombie, "ClimbFenceFlopped") then
        return "fenceAssist"
    end
    if variable(zombie, "ClimbWindowStarted")
            or variable(zombie, "ClimbWindowFlopped") then
        return "windowAssist"
    end
    return nil
end

local function tagTraversal(zombie)
    local killType = traversalType(zombie)
    local data = killType and modData(zombie) or nil
    if data then data[TAG_KEY] = killType end
    return killType
end

local function stillRecovering(zombie)
    if traversalType(zombie) then return true end
    if zombie.isProne and zombie:isProne() then return true end
    return zombie.isGettingUp and zombie:isGettingUp() == true
end

local function onZombieUpdate(zombie)
    if not activeRun or not zombie then return end
    if tagTraversal(zombie) then return end
    local data = existingModData(zombie)
    if not data then return end
    if data[TAG_KEY] and not stillRecovering(zombie) then
        data[TAG_KEY] = nil
    end
end

local function onHitZombie(zombie, wielder)
    if not activeRun or wielder ~= activePlayer or not zombie then return end
    tagTraversal(zombie)
end

local function postureType(zombie)
    if not zombie.isProne or not zombie:isProne() then return "standing" end
    if zombie.isFallOnFront and zombie:isFallOnFront() then
        return "onfront"
    end
    return "onback"
end

function ZombieKillTypeTracker.record(zombie)
    if not activeRun or not zombie then return nil end
    local data = existingModData(zombie)
    local killType = data and data[TAG_KEY] or nil
    if killType ~= "fenceAssist" and killType ~= "windowAssist" then
        killType = postureType(zombie)
    end

    activeRun.zombieKillTypes[killType] =
        math.max(0, math.floor(tonumber(
            activeRun.zombieKillTypes[killType]) or 0)) + 1
    if data then data[TAG_KEY] = nil end
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Kills] Kill type: " .. killType)
    end
    return killType
end

function ZombieKillTypeTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    run.zombieKillTypes =
        type(run.zombieKillTypes) == "table" and run.zombieKillTypes or {}
    for _, killType in ipairs(TYPES) do
        run.zombieKillTypes[killType] = math.max(0,
            math.floor(tonumber(run.zombieKillTypes[killType]) or 0))
    end
end

ZombieKillTypeTracker.onZombieUpdate = onZombieUpdate
ZombieKillTypeTracker.onHitZombie = onHitZombie
ZombieKillTypeTracker.TAG_KEY = TAG_KEY
ZombieKillTypeTracker.TYPES = TYPES

Events.OnZombieUpdate.Add(onZombieUpdate)
Events.OnHitZombie.Add(onHitZombie)

return ZombieKillTypeTracker
