require("TimedActions/ISReadABook")

local Recorder = require("TGSRR/Run/Recorder")
local ItemTypes = require("TGSRR/Run/EntertainmentLiteratureTypes")
local EntertainmentTracker = {}
local activeRun, activePlayer
local installed = false
local completed = setmetatable({}, { __mode = "k" })

local function eligible(item)
    if not item then return nil end
    local id = item:getFullType()
    if not ItemTypes[id] or SkillBook[item:getSkillTrained()] then return nil end
    local recipes = item:getLearnedRecipes()
    if recipes and not recipes:isEmpty() then return nil end
    if item:hasModData() and item:getModData().learnedRecipe then return nil end
    return id
end

local function install()
    if installed then return end
    installed = true
    local originalComplete = ISReadABook.complete
    ISReadABook.complete = function(action)
        -- Capture type before vanilla consumes crosswords and word searches.
        local run = activeRun
        local id = eligible(action.item)
        local canRecord = run and run.lifecycle == "active"
            and Recorder.getActiveRun() == run and Recorder.isActive()
            and action.character == activePlayer and not completed[action]
            and not action.forceStopped and not isServer() and not isClient()
        local result = originalComplete(action)
        if result == true and id and canRecord and activeRun == run
                and run.lifecycle == "active" and Recorder.isActive() then
            completed[action] = true
            local counts = run.entertainment.literature
            counts[id] = (counts[id] or 0) + 1
        end
        return result
    end
end

function EntertainmentTracker.initialize(run, player, created)
    activeRun, activePlayer = run, player
    completed = setmetatable({}, { __mode = "k" })
    if created then
        assert(not run.bootstrapped, "entertainment_requires_fresh_run")
        run.entertainment = {
            literature = {},
        }
    end
    assert(type(run.entertainment) == "table"
        and run.entertainment.schema == nil
        and run.entertainment.partial == nil
        and type(run.entertainment.literature) == "table",
        "unsupported_entertainment_state: start a new development run")
    assert(not run.dailyState or type(run.dailyState.entertainmentLiterature) == "table",
        "missing_entertainment_daily_state: start a new development run")
    install()
end

return EntertainmentTracker
