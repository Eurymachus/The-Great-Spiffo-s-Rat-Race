require("Farming/TimedActions/ISSeedActionNew")
require("Farming/TimedActions/ISHarvestPlantAction")
local Recorder = require("TGSRR/Run/Recorder")
local Snapshot = require("TGSRR/Run/FarmingSnapshot")
local Tracker = {}
local activeRun, activePlayer
local installed = false
local yields = setmetatable({}, {__mode = "k"})
local completed = setmetatable({}, {__mode = "k"})

local function eligible(action)
    return activeRun and activeRun.lifecycle == "active" and Recorder.isActive()
        and Recorder.getActiveRun() == activeRun and action.character == activePlayer
        and not completed[action] and not action.forceStopped
        and not isClient() and not isServer()
end
local function plantFor(action)
    return SFarmingSystem.instance:getLuaObjectAt(action.plant.x, action.plant.y, action.plant.z)
end
local function add(counts, id, count)
    counts[id] = (counts[id] or 0) + count
end
local function outputCounts(character, ids)
    local counts = {}
    local items = character:getInventory():getItems()
    for i = 0, items:size() - 1 do
        local id = items:get(i):getFullType()
        if ids[id] then add(counts, id, 1) end
    end
    return counts
end
local function install()
    if installed then return end
    installed = true
    local rollYield = getVegetablesNumber
    getVegetablesNumber = function(minimum, maximum, allowedMin, allowedMax, plant, skill)
        local count = rollYield(minimum, maximum, allowedMin, allowedMax, plant, skill)
        -- Weak per-plant evidence, not an in-progress guard or retained action log.
        yields[plant] = {count = count}
        return count
    end
    local sow = ISSeedActionNew.complete
    ISSeedActionNew.complete = function(action)
        local run = activeRun
        local plant = eligible(action) and plantFor(action) or nil
        local wasPloughed = plant and plant.state == "plow"
        local result = sow(action)
        if result == true and wasPloughed and activeRun == run and eligible(action)
                and plant.state == "seeded" and plant.typeOfSeed == action.typeOfSeed then
            completed[action] = true
            add(run.farming.planted, action.typeOfSeed, 1)
        end
        return result
    end
    local harvest = ISHarvestPlantAction.complete
    ISHarvestPlantAction.complete = function(action)
        local run = activeRun
        local plant = eligible(action) and plantFor(action) or nil
        local ready = plant and plant:canHarvest()
        local crop = ready and plant.typeOfSeed or nil
        local ids, before = {}, nil
        local previousYield = plant and yields[plant]
        if ready then
            local props = farming_vegetableconf.props[crop]
            -- Seeds are a separate product, not harvested produce.
            if props.vegetableName then ids[props.vegetableName] = 1 end
            if props.produceExtra then ids[props.produceExtra] = (ids[props.produceExtra] or 0) + 1 end
            before = outputCounts(action.character, ids)
        end
        local result = harvest(action)
        if result == true and ready and activeRun == run and eligible(action)
                and not plant:canHarvest() then
            local rolled = yields[plant]
            assert(rolled and rolled ~= previousYield, "TGSRR farming: harvest yield was not observed")
            completed[action] = true
            add(run.farming.harvested, crop, 1)
            local after = outputCounts(action.character, ids)
            for id, count in pairs(after) do
                -- Cap actual additions at the rolled produce quantity. Vanilla may
                -- append seed items of this same type after creating produce.
                local delta = math.min(count - (before[id] or 0), math.max(0, rolled.count) * ids[id])
                if delta > 0 then add(run.farming.produce, id, delta) end
            end
        end
        return result
    end
end
function Tracker.initialize(run, player, created)
    activeRun, activePlayer = run, player
    completed = setmetatable({}, {__mode = "k"})
    if not run.farming then
        run.farming = {schema = 1, planted = {}, harvested = {}, produce = {},
            partial = not created or run.bootstrapped == true or nil}
    end
    if run.dailyState and not run.dailyState.farmingPlanted then
        for _, field in ipairs({"Planted", "Harvested", "Produce"}) do
            run.dailyState["farming" .. field] = Snapshot.copy(run.farming[string.lower(field)])
        end
        run.dailyState.farmingPartial = true
    end
    install()
end
return Tracker
