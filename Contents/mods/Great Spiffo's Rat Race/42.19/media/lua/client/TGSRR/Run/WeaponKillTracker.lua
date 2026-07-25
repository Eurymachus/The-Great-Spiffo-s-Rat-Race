local WeaponKillSnapshot = require "TGSRR/Run/WeaponKillSnapshot"

local WeaponKillTracker = {}

local activeRun = nil
local activePlayer = nil
local lastHit = setmetatable({}, { __mode = "k" })

local HIT_CREDIT_SECONDS = 10
local FIRE_CREDIT_SECONDS = 1

local function nowSeconds()
    if getTimestampMs then return getTimestampMs() / 1000 end
    if getTimestamp then return getTimestamp() end
    return os.time()
end

local function onFire(zombie)
    if not zombie or not zombie.isOnFire then return false end
    local ok, value = pcall(function() return zombie:isOnFire() end)
    return ok and value == true
end

local function playerDriving(player)
    local vehicle = player and player.getVehicle and player:getVehicle() or nil
    if not vehicle then return false end
    if vehicle.getDriverRegardlessOfTow
            and vehicle:getDriverRegardlessOfTow() == player then return true end
    if vehicle.getDriver and vehicle:getDriver() == player then return true end
    return vehicle.getSeat and vehicle:getSeat(player) == 0 or false
end

local function recentHit(zombie, player, maxAge)
    local hit = lastHit[zombie]
    if not hit or hit.player ~= player then return nil end
    if nowSeconds() - hit.time > maxAge then return nil end
    return hit
end

local function record(sourceId)
    if not activeRun then return end
    activeRun.weaponKills = type(activeRun.weaponKills) == "table"
        and activeRun.weaponKills or {}
    activeRun.weaponKills[sourceId] =
        (tonumber(activeRun.weaponKills[sourceId]) or 0) + 1
end

local function onWeaponHitCharacter(attacker, target, weapon)
    if attacker ~= activePlayer or not target
            or not instanceof(target, "IsoZombie") then return end
    lastHit[target] = {
        player = attacker,
        weaponId = WeaponKillSnapshot.weaponId(weapon),
        time = nowSeconds(),
    }
end

local function onZombieDead(zombie)
    if not activeRun or not activePlayer or not zombie then return end
    if zombie.isFakeDead and zombie:isFakeDead() then return end

    local killer = zombie.getAttackedBy and zombie:getAttackedBy() or nil
    local burning = onFire(zombie)
    if burning and killer ~= activePlayer then
        activeRun.fireDeaths =
            math.max(0, tonumber(activeRun.fireDeaths) or 0) + 1
    end
    if killer ~= activePlayer then
        lastHit[zombie] = nil
        return
    end

    local hit = recentHit(zombie, activePlayer,
        burning and FIRE_CREDIT_SECONDS or HIT_CREDIT_SECONDS)
    local vehicleCollision = zombie.isVehicleCollision
        and zombie:isVehicleCollision() == true
    local sourceId
    if vehicleCollision then
        sourceId = WeaponKillSnapshot.VEHICLE
    elseif hit then
        sourceId = hit.weaponId
    elseif playerDriving(activePlayer) then
        sourceId = WeaponKillSnapshot.VEHICLE
    else
        local weapon = activePlayer.getAttackingWeapon
            and activePlayer:getAttackingWeapon() or nil
        sourceId = weapon and WeaponKillSnapshot.weaponId(weapon)
            or WeaponKillSnapshot.UNKNOWN
    end
    record(sourceId or WeaponKillSnapshot.UNKNOWN)
    lastHit[zombie] = nil
end

function WeaponKillTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    run.weaponKills = type(run.weaponKills) == "table" and run.weaponKills or {}
    run.fireDeaths = math.max(0, math.floor(tonumber(run.fireDeaths) or 0))
    local dailyState = run.dailyState
    if type(dailyState) == "table" and type(dailyState.weaponKills) ~= "table" then
        dailyState.weaponKills = WeaponKillSnapshot.copy(run.weaponKills)
        dailyState.weaponKillsPartial = true
    end
    if type(dailyState) == "table" and dailyState.fireDeaths == nil then
        dailyState.fireDeaths = run.fireDeaths
        dailyState.fireDeathsPartial = true
    end
end

Events.OnWeaponHitCharacter.Add(onWeaponHitCharacter)
Events.OnZombieDead.Add(onZombieDead)

return WeaponKillTracker
