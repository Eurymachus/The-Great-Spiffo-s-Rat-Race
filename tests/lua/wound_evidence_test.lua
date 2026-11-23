local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. package.path
BodyPartType = {ToString=function(value) return value end}
local bite, scratch, bandaged, bleeding, attackAge = 0, 0, false, 10, 0
local attacker = nil
local part = {
    getType=function() return "ForeArm_L" end,
    getBiteTime=function() return bite end,
    getScratchTime=function() return scratch end,
    getCutTime=function() return 0 end,
    getDeepWoundTime=function() return 0 end,
    bandaged=function() return bandaged end,
    getBleedingTime=function() return bleeding end,
}
local player = {
    getAttackedBy=function() return attacker end,
    getTimeSinceZombieAttack=function() return attackAge end,
    getBodyDamage=function() return {getBodyParts=function()
        return {size=function() return 1 end, get=function() return part end}
    end} end,
}
local W = require("TGSRR/Run/WoundEvidence")
W.reset()
W.observe(player, true)
attacker = {isZombie=function() return true end, getAttackDidDamage=function() return true end}
scratch = 10
local wounds = W.observe(player)
assert(wounds[1].zombieAssociation == "observed_zombie_attack")
assert(W.supportsZombieBleeding(wounds))
attackAge, bandaged = 10000, true
assert(not W.supportsZombieBleeding(W.observe(player)))
bandaged = false
assert(W.supportsZombieBleeding(W.observe(player)))
scratch = 0
assert(#W.observe(player) == 0)
scratch = 10
assert(not W.supportsZombieBleeding(W.observe(player))) -- Stale attacker.
W.reset()
attackAge = 0
assert(not W.supportsZombieBleeding(W.observe(player, true))) -- Reload baseline.
bite = 10
assert(W.supportsZombieBleeding(W.observe(player)))
bleeding = 0
assert(not W.supportsZombieBleeding(W.observe(player)))
assert(wounds[1].bleedingTime == 10) -- Captured evidence is detached.
print("wound evidence tests passed")
