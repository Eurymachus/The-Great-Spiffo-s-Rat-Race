local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

Perks = { None = "None" }

local perks = {
    {
        getType = function() return "Aiming" end,
        getParent = function() return "Firearm" end,
    },
    {
        getType = function() return "Cooking" end,
        getParent = function() return "Crafting" end,
    },
}

PerkFactory = {
    PerkList = {
        size = function() return #perks end,
        get = function(_, index) return perks[index + 1] end,
    },
}

local levels = { Aiming = 2, Cooking = 0 }
local experience = { Aiming = 88.5, Cooking = 0 }
local xp = {
    getXP = function(_, perkType) return experience[perkType] end,
}
local player = {
    getXp = function() return xp end,
    getPerkLevel = function(_, perkType) return levels[perkType] end,
}

local SkillSnapshot = require "TGSRR/Run/SkillSnapshot"
local observed = SkillSnapshot.observe(player)

assert(#observed == 1, "zero skills must be omitted from sparse export")
assert(observed[1].id == "Aiming", "observed skill ID must be retained")
assert(observed[1].categoryId == "Firearm", "skill category must be retained")
assert(observed[1].level == 2, "skill level must be retained")
assert(observed[1].xp == 88.5, "skill XP must be retained")

print("skill_snapshot_test: ok")
