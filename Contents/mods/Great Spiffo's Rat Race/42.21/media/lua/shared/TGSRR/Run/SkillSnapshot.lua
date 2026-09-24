local SkillSnapshot = {}

local function eachSkill(visitor)
    local perks = PerkFactory and PerkFactory.PerkList or nil
    if not perks then return end
    for index = 0, perks:size() - 1 do
        local perk = perks:get(index)
        if perk and perk:getParent() ~= Perks.None then visitor(perk) end
    end
end

function SkillSnapshot.totals(player)
    local result = {}
    local xp = player and player.getXp and player:getXp() or nil
    if not xp then return result end
    eachSkill(function(perk)
        local perkType = perk:getType()
        result[tostring(perkType)] = math.max(0, tonumber(xp:getXP(perkType)) or 0)
    end)
    return result
end

function SkillSnapshot.observe(player)
    local result = {}
    local xp = player and player.getXp and player:getXp() or nil
    if not player or not xp then return result end
    eachSkill(function(perk)
        local perkType = perk:getType()
        local level = math.max(0, math.min(10,
            math.floor(tonumber(player:getPerkLevel(perkType)) or 0)))
        local currentXp = math.max(0, tonumber(xp:getXP(perkType)) or 0)
        if level == 0 and currentXp == 0 then return end
        result[#result + 1] = {
            id = tostring(perkType),
            categoryId = tostring(perk:getParent()),
            level = level,
            xp = currentXp,
        }
    end)
    table.sort(result, function(a, b) return a.id < b.id end)
    return result
end

return SkillSnapshot
