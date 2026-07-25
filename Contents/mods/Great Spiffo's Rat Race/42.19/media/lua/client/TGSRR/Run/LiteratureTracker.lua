require "TimedActions/ISReadABook"

local Identity = require "TGSRR/Run/Identity"
local Recorder = require "TGSRR/Run/Recorder"

local LiteratureTracker = {}

local activeRun = nil
local activePlayer = nil
local installed = false
local originalComplete = nil

local function javaList(values)
    local result = {}
    if not values then return result end
    for index = 0, values:size() - 1 do
        result[#result + 1] = tostring(values:get(index))
    end
    table.sort(result)
    return result
end

local function merge(values, additions)
    local seen = {}
    for _, value in ipairs(values or {}) do seen[tostring(value)] = true end
    values = values or {}
    for _, value in ipairs(additions or {}) do
        value = tostring(value)
        if value ~= "" and not seen[value] then
            seen[value] = true
            values[#values + 1] = value
        end
    end
    table.sort(values)
    return values
end

local function classification(item)
    if not item then return nil end
    if SkillBook[item:getSkillTrained()] then return "skill_book" end
    local recipes = item:getLearnedRecipes()
    if recipes and not recipes:isEmpty() then return "recipe_literature" end
    return nil
end

local function baseline(player, partial)
    local itemSet = {}
    local eligibleIds = {}
    local allItems = getScriptManager():getAllItems()
    for index = 0, allItems:size() - 1 do
        local item = allItems:get(index)
        if item:isItemType(ItemType.LITERATURE) and classification(item) then
            local fullType = tostring(item:getFullName())
            eligibleIds[fullType] = true
            local pages = tonumber(item:getNumberOfPages()) or 0
            if pages > 0 and player:getAlreadyReadPages(fullType) >= pages then
                itemSet[fullType] = true
            end
        end
    end
    local alreadyRead = player:getAlreadyReadBook()
    for index = 0, alreadyRead:size() - 1 do
        local id = tostring(alreadyRead:get(index))
        if eligibleIds[id] then itemSet[id] = true end
    end

    local itemIds = {}
    for id, _ in pairs(itemSet) do itemIds[#itemIds + 1] = id end
    table.sort(itemIds)
    local gameTime = getGameTime()
    return {
        capturedUtc = Identity.utcSeconds(),
        worldAgeHours = gameTime and gameTime:getWorldAgeHours() or 0,
        partial = partial == true,
        itemIds = itemIds,
        literatureTitles = {},
        printMediaIds = {},
    }
end

local function recordCompletion(action, item, wasComplete)
    if not activeRun or action.character ~= activePlayer or wasComplete then return end
    if isServer and isServer() then return end

    local id = tostring(item:getFullType())
    local kind = classification(item)
    if not kind then return end
    local recipes = javaList(item:getLearnedRecipes())
    local mediaIds = {}
    local titles = {}
    local recorded, event = Recorder.record("literature.read", {
        itemId = id,
        classification = kind,
        learnedRecipeIds = recipes,
        literatureTitles = titles,
        printMediaIds = mediaIds,
    })
    if not recorded then return end

    local completed = activeRun.literature.completed
    local record = completed[id]
    if type(record) ~= "table" then
        record = {
            classification = kind,
            completions = 0,
            firstCompletionUtc = event.utc,
            firstCompletionWorldAgeHours = event.worldAgeHours,
            learnedRecipeIds = recipes,
            literatureTitles = titles,
            printMediaIds = mediaIds,
        }
        completed[id] = record
    end
    record.completions = math.max(0,
        math.floor(tonumber(record.completions) or 0)) + 1
    record.lastCompletionUtc = event.utc
    record.lastCompletionWorldAgeHours = event.worldAgeHours
    record.learnedRecipeIds = merge(record.learnedRecipeIds, recipes)
    record.literatureTitles = merge(record.literatureTitles, titles)
    record.printMediaIds = merge(record.printMediaIds, mediaIds)

    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Literature] Read " .. id .. " (" .. kind .. ")")
    end
end

local function sanitizeExisting(state)
    local baselineValue = state.baseline
    local filteredIds = {}
    for _, id in ipairs(baselineValue.itemIds or {}) do
        id = tostring(id)
        local item = getScriptManager():FindItem(id)
        if classification(item) then filteredIds[#filteredIds + 1] = id end
    end
    table.sort(filteredIds)
    baselineValue.itemIds = filteredIds
    baselineValue.literatureTitles = {}
    baselineValue.printMediaIds = {}

    local filteredCompleted = {}
    for id, record in pairs(state.completed or {}) do
        if type(record) == "table"
                and (record.classification == "skill_book"
                    or record.classification == "recipe_literature") then
            record.literatureTitles = {}
            record.printMediaIds = {}
            filteredCompleted[tostring(id)] = record
        end
    end
    state.completed = filteredCompleted
end

local function install()
    if installed then return end
    installed = true
    originalComplete = ISReadABook.complete
    ISReadABook.complete = function(action)
        local item = action and action.item or nil
        local wasComplete = false
        if item then
            local pages = tonumber(item:getNumberOfPages()) or 0
            local startPage = tonumber(action.startPage)
                or tonumber(item:getAlreadyReadPages()) or 0
            wasComplete = pages > 0 and startPage >= pages
        end
        local result = originalComplete(action)
        if result == true and item then
            recordCompletion(action, item, wasComplete)
        end
        return result
    end
end

function LiteratureTracker.initialize(run, player, created)
    activeRun = run
    activePlayer = player
    install()

    if type(run.literature) == "table"
            and type(run.literature.baseline) == "table" then
        run.literature.completed = type(run.literature.completed) == "table"
            and run.literature.completed or {}
        sanitizeExisting(run.literature)
        return true
    end

    local value = baseline(player, not created or run.bootstrapped == true)
    local recorded, reason = Recorder.record("literature.baseline", {
        partial = value.partial,
        itemIds = value.itemIds,
        literatureTitles = value.literatureTitles,
        printMediaIds = value.printMediaIds,
    }, {
        utc = value.capturedUtc,
        worldAgeHours = value.worldAgeHours,
    })
    if not recorded then return false, reason end
    run.literature = {
        schema = 1,
        partial = value.partial,
        baseline = value,
        completed = {},
    }
    if isDebugEnabled and isDebugEnabled() then
        print("[TGSRR Literature] Baseline: " .. #value.itemIds
            .. " items, " .. #value.literatureTitles .. " titles, "
            .. #value.printMediaIds .. " print media"
            .. (value.partial and " (partial)" or ""))
    end
    return true
end

return LiteratureTracker
