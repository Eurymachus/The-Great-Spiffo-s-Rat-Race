local InjurySnapshot = require "TGSRR/Run/InjurySnapshot"

local InjuryTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false

local function positive(value)
    return (tonumber(value) or 0) > 0
end

local function bodyPartId(part)
    local value = part and part:getType() or nil
    if value and BodyPartType and BodyPartType.ToString then
        return tostring(BodyPartType.ToString(value))
    end
    return value and tostring(value) or "Unknown"
end

local function states(part)
    return {
        bite = part:bitten() == true,
        scratch = part:scratched() == true,
        laceration = part:isCut() == true,
        deep_wound = part:isDeepWounded() == true,
        fracture = positive(part:getFractureTime()),
        lodged_glass = part:haveGlass() == true,
        lodged_bullet = part:haveBullet() == true,
        burn = positive(part:getBurnTime()),
    }
end

local function observe(player)
    local result = {}
    local damage = player and player:getBodyDamage() or nil
    local parts = damage and damage:getBodyParts() or nil
    if not parts then return result end
    for index = 0, parts:size() - 1 do
        local part = parts:get(index)
        local partId = bodyPartId(part)
        for injuryType, active in pairs(states(part)) do
            result[InjurySnapshot.key(injuryType, partId)] = active
        end
    end
    return result
end

local function zombieAssociated(player)
    local attacker = player and player:getAttackedBy() or nil
    if not attacker or not attacker.isZombie or not attacker:isZombie() then
        return false
    end
    if not attacker.getAttackDidDamage then return false end
    local ok, didDamage = pcall(function()
        return attacker:getAttackDidDamage()
    end)
    return ok and didDamage == true
end

local function increment(values, key)
    values[key] = math.max(0,
        math.floor(tonumber(values[key]) or 0)) + 1
end

local function update(player)
    if not activeRun or player ~= activePlayer then return end
    if isServer and isServer() then return end

    local current = observe(player)
    local previous = activeRun.injuryObservedState or {}
    local associated = zombieAssociated(player)
    for key, active in pairs(current) do
        if active and previous[key] ~= true then
            increment(activeRun.injuries, key)
            activeRun.injuriesTotal =
                math.max(0, math.floor(
                    tonumber(activeRun.injuriesTotal) or 0)) + 1
            if associated then
                increment(activeRun.zombieAssociatedInjuries, key)
                activeRun.zombieAssociatedInjuriesTotal =
                    math.max(0, math.floor(tonumber(
                        activeRun.zombieAssociatedInjuriesTotal) or 0)) + 1
            end
            if isDebugEnabled and isDebugEnabled() then
                local injuryType, bodyPart = InjurySnapshot.split(key)
                print("[TGSRR Injuries] " .. injuryType .. " on "
                    .. bodyPart
                    .. (associated and " (zombie-associated)" or ""))
            end
        end
    end
    activeRun.injuryObservedState = current
end

local function install()
    if installed then return end
    installed = true
    Events.OnPlayerUpdate.Add(update)
end

function InjuryTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
    if type(run.injuryObservedState) ~= "table" then
        run.injuryObservedState = observe(player)
    end
end

return InjuryTracker
