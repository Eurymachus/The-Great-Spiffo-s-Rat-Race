require "TimedActions/Fishing/TimedActions/ISPickupFishAction"

local FishCaughtTracker = {}

local ITEM_MARKER = "TGSRR_FishCaughtRunId"
local activeRun = nil
local activePlayer = nil
local installed = false

local function record(action)
    if not activeRun or not action or action.character ~= activePlayer
            or action.isFish ~= true or not action.item then
        return false
    end
    if isServer and isServer() then return false end
    local item = action.item
    local fishId = item:getFullType()
    if not fishId or fishId == "" then return false end
    local modData = item:getModData()
    if modData[ITEM_MARKER] == activeRun.runId then return false end
    modData[ITEM_MARKER] = activeRun.runId

    activeRun.fishCaught[fishId] =
        math.max(0, math.floor(tonumber(
            activeRun.fishCaught[fishId]) or 0)) + 1
    activeRun.fishCaughtTotal =
        math.max(0, math.floor(tonumber(
            activeRun.fishCaughtTotal) or 0)) + 1
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Fishing] Caught " .. fishId)
    end
    return true
end

local function install()
    if installed then return end
    installed = true
    local originalNew = ISPickupFishAction.new
    ISPickupFishAction.new = function(self, character, rod, fish)
        local action = originalNew(self, character, rod, fish)
        record(action)
        return action
    end
end

function FishCaughtTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    install()
end

return FishCaughtTracker
