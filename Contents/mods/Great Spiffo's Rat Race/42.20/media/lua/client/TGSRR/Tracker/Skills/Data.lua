local ChallengeEvents = require "TGSRR/Core/Events"

local Data = {}
local dirty = true
local cachedPlayer = nil
local cachedSnapshot = nil

local function sortByName(a, b)
    return string.lower(a.name) < string.lower(b.name)
end

local function previousXp(perk, level)
    if level <= 0 then return 0 end
    return perk:getTotalXpForLevel(level)
end

local function skillProgress(player, perk)
    local perkType = perk:getType()
    local level = math.max(0, math.min(10, player:getPerkLevel(perkType)))
    if level >= 10 then return level, 1, 10 end

    local fromXp = previousXp(perk, level)
    local toXp = perk:getTotalXpForLevel(level + 1)
    local required = math.max(0, toXp - fromXp)
    local current = math.max(0, player:getXp():getXP(perkType) - fromXp)
    local progress = required > 0 and math.min(1, current / required) or 0
    return level, progress, level + progress, current, required
end

local function discover(player)
    local categoriesByType = {}
    local categories = {}
    for index = 0, PerkFactory.PerkList:size() - 1 do
        local perk = PerkFactory.PerkList:get(index)
        if perk and perk:getParent() ~= Perks.None then
            local parentType = perk:getParent()
            local key = tostring(parentType)
            local category = categoriesByType[key]
            if not category then
                local parent = PerkFactory.getPerk(parentType)
                category = {
                    id = key,
                    name = parent and parent:getName() or key,
                    skills = {},
                }
                categoriesByType[key] = category
                categories[#categories + 1] = category
            end

            local level, levelProgress, totalProgress, currentXp, requiredXp = skillProgress(player, perk)
            category.skills[#category.skills + 1] = {
                id = tostring(perk:getType()),
                name = perk:getName(),
                perk = perk:getType(),
                categoryId = category.id,
                categoryName = category.name,
                level = level,
                levelProgress = levelProgress,
                totalProgress = totalProgress,
                currentXp = currentXp,
                requiredXp = requiredXp,
                xpBoost = player:getXp():getPerkBoost(perk:getType()),
                complete = level >= 10,
            }
        end
    end

    table.sort(categories, sortByName)
    for _, category in ipairs(categories) do table.sort(category.skills, sortByName) end
    return categories
end

function Data.refresh(player)
    if not player then
        cachedPlayer = nil
        cachedSnapshot = { available = false, categories = {}, rows = {}, mastered = 0, total = 0, percent = 0 }
        dirty = false
        return cachedSnapshot
    end

    local categories = discover(player)
    local rows = {}
    local mastered = 0
    local progress = 0
    local total = 0
    for _, category in ipairs(categories) do
        category.mastered = 0
        category.total = #category.skills
        category.totalProgress = 0
        for _, skill in ipairs(category.skills) do
            category.totalProgress = category.totalProgress + skill.totalProgress
            if skill.complete then category.mastered = category.mastered + 1 end
        end
        category.percent = category.total > 0 and
            category.totalProgress / (category.total * 10) * 100 or 0
        rows[#rows + 1] = {
            kind = "category",
            id = "category:" .. category.id,
            name = category.name,
            category = category,
        }
        for _, skill in ipairs(category.skills) do
            rows[#rows + 1] = { kind = "skill", id = skill.id, skill = skill }
        end
        total = total + category.total
        progress = progress + category.totalProgress
        mastered = mastered + category.mastered
    end

    cachedPlayer = player
    cachedSnapshot = {
        available = true,
        categories = categories,
        rows = rows,
        mastered = mastered,
        total = total,
        percent = total > 0 and progress / (total * 10) * 100 or 0,
    }
    dirty = false
    return cachedSnapshot
end

function Data.getSnapshot(player)
    if dirty or cachedPlayer ~= player or not cachedSnapshot then return Data.refresh(player) end
    return cachedSnapshot
end

function Data.markDirty()
    dirty = true
end

function Data.isDirty()
    return dirty
end

local function onAddXp(player)
    if player == (getSpecificPlayer(0) or getPlayer()) then Data.markDirty() end
end

local function onLevelPerk(player, perkType, level)
    if player ~= (getSpecificPlayer(0) or getPlayer()) then return end
    Data.markDirty()
    local perk = perkType and PerkFactory.getPerk(perkType) or nil
    local parent = perk and PerkFactory.getPerk(perk:getParent()) or nil
    ChallengeEvents.emit("skill.level.reached", {
        player = player,
        skillId = perk and tostring(perk:getType()) or tostring(perkType),
        skillName = perk and perk:getName() or tostring(perkType),
        categoryId = parent and tostring(parent:getType()) or nil,
        categoryName = parent and parent:getName() or nil,
        level = level,
    })
end

Events.AddXP.Add(onAddXp)
Events.LevelPerk.Add(onLevelPerk)

return Data
