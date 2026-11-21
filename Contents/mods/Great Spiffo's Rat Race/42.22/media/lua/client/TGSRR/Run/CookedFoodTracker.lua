require("TimedActions/ISTransferAction")
require("TimedActions/ISGrabItemAction")

local Recorder = require("TGSRR/Run/Recorder")
local Snapshot = require("TGSRR/Run/CookedFoodSnapshot")
local Tracker = {}
local activeRun, activePlayer
local installed = false
local marker = "TGSRRCookedFoodRunId"

local function eligible(item)
    return instanceof(item, "Food") and not item:isBurnt()
        and (item:isCooked() or item:hasTag(ItemTag.ALREADY_COOKED))
end

local function visit(item, baseline)
    if eligible(item) then
        local data = item:getModData()
        if data[marker] ~= activeRun.runId then
            if not baseline then
                local id = item:getFullType()
                local counts = activeRun.cookedFood.items
                counts[id] = (counts[id] or 0) + 1
            end
            data[marker] = activeRun.runId
        end
    end
    if instanceof(item, "InventoryContainer") then
        local items = item:getInventory():getItems()
        for i = 0, items:size() - 1 do visit(items:get(i), baseline) end
    end
end

local function active(character)
    return activeRun and activeRun.lifecycle == "active"
        and Recorder.getActiveRun() == activeRun and Recorder.isActive()
        and character == activePlayer and not isClient() and not isServer()
end

local function collected(character, item, wasOwned)
    if wasOwned or not active(character) or not item then return end
    local container = item:getContainer()
    if container and container:isInCharacterInventory(character) then visit(item, false) end
end

local function install()
    if installed then return end
    installed = true
    local transfer = ISTransferAction.transferItem
    ISTransferAction.transferItem = function(self, character, item, source, destination, square)
        local wasOwned = source and source:isInCharacterInventory(character)
        local result = transfer(self, character, item, source, destination, square)
        collected(character, result, wasOwned)
        return result
    end
    local grab = ISGrabItemAction.transferItem
    ISGrabItemAction.transferItem = function(action, item)
        local inventoryItem = action.item and action.item:getItem()
        local result = grab(action, item)
        collected(action.character, inventoryItem, false)
        return result
    end
end

function Tracker.initialize(run, player, created)
    activeRun, activePlayer = run, player
    if not run.cookedFood then
        run.cookedFood = {schema = 1, items = {},
            partial = not created or run.bootstrapped == true or nil}
        -- Baseline existing possessions once, never on ordinary reloads.
        local items = player:getInventory():getItems()
        for i = 0, items:size() - 1 do visit(items:get(i), true) end
    end
    if run.dailyState and not run.dailyState.cookedFoodItems then
        run.dailyState.cookedFoodItems = Snapshot.copy(run.cookedFood.items)
        run.dailyState.cookedFoodPartial = true
    end
    install()
end

return Tracker
