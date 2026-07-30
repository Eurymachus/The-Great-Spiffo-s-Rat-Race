local BrokenWeaponTracker = {}

local activeRun = nil
local activePlayer = nil
local countedItems = setmetatable({}, { __mode = "k" })
local trackedSwing = nil
local wrappedOnBreak = {}
local TRACK_TICKS = 240

local function isWeapon(item)
    if not item then return false end
    local ok, result = pcall(function()
        return instanceof(item, "HandWeapon")
    end)
    if not ok or not result then return false end
    local id = item.getFullType and item:getFullType() or nil
    return id and id ~= "" and id ~= "Base.BareHands"
end

local function condition(item)
    if not item or not item.getCondition then return nil end
    local ok, value = pcall(function() return item:getCondition() end)
    return ok and tonumber(value) or nil
end

local function fullType(item)
    if not item or not item.getFullType then return nil end
    local ok, value = pcall(function() return item:getFullType() end)
    return ok and value and tostring(value) or nil
end

function BrokenWeaponTracker.record(player, item, originalFullType)
    if not activeRun or player ~= activePlayer then return false end
    if not isWeapon(item) and not originalFullType then return false end
    if item and countedItems[item] then return false end

    local id = originalFullType or fullType(item)
    if not id or id == "" or id == "Base.BareHands" then return false end
    if item then countedItems[item] = true end
    activeRun.brokenWeapons[id] =
        math.max(0, math.floor(
            tonumber(activeRun.brokenWeapons[id]) or 0)) + 1
    activeRun.brokenWeaponsTotal =
        math.max(0, math.floor(
            tonumber(activeRun.brokenWeaponsTotal) or 0)) + 1
    return true
end

function BrokenWeaponTracker.installOnBreakWrappers()
    if type(OnBreak) ~= "table" then return end
    for name, callback in pairs(OnBreak) do
        if type(callback) == "function"
                and wrappedOnBreak[name] ~= callback then
            local original = callback
            local wrapper = function(item, player, ...)
                BrokenWeaponTracker.record(player, item)
                return original(item, player, ...)
            end
            wrappedOnBreak[name] = wrapper
            OnBreak[name] = wrapper
        end
    end
end

function BrokenWeaponTracker.onWeaponSwing(player, weapon)
    if not activeRun or player ~= activePlayer or not isWeapon(weapon) then
        return
    end
    local currentCondition = condition(weapon)
    if not currentCondition or currentCondition <= 0 then return end
    trackedSwing = {
        item = weapon,
        fullType = fullType(weapon),
        ticksLeft = TRACK_TICKS,
    }
end

function BrokenWeaponTracker.onPlayerUpdate(player)
    if player ~= activePlayer or not trackedSwing then return end
    local tracked = trackedSwing
    tracked.ticksLeft = tracked.ticksLeft - 1
    local currentCondition = condition(tracked.item)
    if countedItems[tracked.item] then
        trackedSwing = nil
    elseif currentCondition and currentCondition <= 0 then
        BrokenWeaponTracker.record(player, tracked.item, tracked.fullType)
        trackedSwing = nil
    elseif not currentCondition or tracked.ticksLeft <= 0 then
        trackedSwing = nil
    end
end

function BrokenWeaponTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    trackedSwing = nil
    BrokenWeaponTracker.installOnBreakWrappers()
end

Events.OnGameStart.Add(BrokenWeaponTracker.installOnBreakWrappers)
Events.OnWeaponSwing.Add(BrokenWeaponTracker.onWeaponSwing)
Events.OnPlayerUpdate.Add(BrokenWeaponTracker.onPlayerUpdate)

return BrokenWeaponTracker
