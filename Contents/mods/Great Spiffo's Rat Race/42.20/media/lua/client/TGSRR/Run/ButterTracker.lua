require "Entity/ISUI/CraftRecipe/ISWidgetHandCraftControl"

local ButterTracker = {}

local RECIPE_NAME = "churn_butter"
local BUTTER_ID = "Base.Butter"

local activeRun = nil
local activePlayer = nil
local installed = false
local pendingByControl = setmetatable({}, { __mode = "k" })

local function recipeName(control, action)
    local recipe = action and action.craftRecipe or nil
    if not recipe and control and control.logic
            and control.logic.getRecipe then
        recipe = control.logic:getRecipe()
    end
    return recipe and recipe:getName() or nil
end

local function install()
    if installed then return end
    installed = true

    local originalStart =
        ISWidgetHandCraftControl.onHandcraftActionStart
    ISWidgetHandCraftControl.onHandcraftActionStart =
        function(control, action)
            local relevant = control and control.player == activePlayer
                and recipeName(control, action) == RECIPE_NAME
            local result = originalStart(control, action)
            if relevant then
                pendingByControl[control] =
                    (pendingByControl[control] or 0) + 1
                if isDebugEnabled and isDebugEnabled() then
                    print("[TGSRR Animals] Started " .. RECIPE_NAME)
                end
            end
            return result
        end

    local originalComplete =
        ISWidgetHandCraftControl.onHandcraftActionComplete
    ISWidgetHandCraftControl.onHandcraftActionComplete = function(control)
        local pending = pendingByControl[control] or 0
        local result = originalComplete(control)
        if pending > 0 and activeRun then
            pendingByControl[control] = pending - 1
            activeRun.butterProduced =
                math.max(0, math.floor(tonumber(
                    activeRun.butterProduced) or 0)) + 1
            if isDebugEnabled and isDebugEnabled() then
                print("[TGSRR Animals] Produced " .. BUTTER_ID)
            end
        end
        return result
    end

    local originalCancelled =
        ISWidgetHandCraftControl.onHandcraftActionCancelled
    ISWidgetHandCraftControl.onHandcraftActionCancelled = function(control)
        local pending = pendingByControl[control] or 0
        local result = originalCancelled(control)
        if pending > 0 then pendingByControl[control] = pending - 1 end
        return result
    end
end

function ButterTracker.initialize(run, player)
    activeRun = run
    activePlayer = player
    pendingByControl = setmetatable({}, { __mode = "k" })
    install()
end

return ButterTracker
