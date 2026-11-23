local WoundEvidence = {}
local tracked = {}
local kinds = { "bite", "scratch", "laceration", "deep_wound" }

local function recentZombieAttack(player)
    local attacker = player:getAttackedBy()
    -- This timer counts character updates, not real milliseconds. The retained
    -- attacker/AttackDidDamage pair alone can remain stale after an attack.
    return attacker and attacker:isZombie() and attacker:getAttackDidDamage()
        and player:getTimeSinceZombieAttack() <= 1
end

function WoundEvidence.reset()
    tracked = {}
end

function WoundEvidence.observe(player, baseline)
    local body = player:getBodyDamage()
    local parts = body and body:getBodyParts()
    if not parts then return nil end
    local result, current = {}, {}
    local associated = not baseline and recentZombieAttack(player)
    for index = 0, parts:size() - 1 do
        local part = parts:get(index)
        local bodyPart = tostring(BodyPartType.ToString(part:getType()))
        local times = { part:getBiteTime(), part:getScratchTime(),
            part:getCutTime(), part:getDeepWoundTime() }
        for i, kind in ipairs(kinds) do
            if times[i] > 0 then
                local key = kind .. "|" .. bodyPart
                local origin = tracked[key]
                if not origin then
                    origin = kind == "bite" and "bite"
                        or (associated and "observed_zombie_attack" or "unknown")
                end
                current[key] = origin
                result[#result + 1] = { injuryType = kind, bodyPart = bodyPart,
                    remainingTime = times[i], bandaged = part:bandaged() == true,
                    bleedingTime = part:getBleedingTime(), zombieAssociation = origin }
            end
        end
    end
    -- At most four wound types per body part. Healing removes provenance;
    -- bandaging does not. Session initialization treats existing wounds as unknown.
    tracked = current
    return result
end

function WoundEvidence.supportsZombieBleeding(wounds)
    for _, wound in ipairs(wounds or {}) do
        if not wound.bandaged and wound.bleedingTime > 0
            and wound.zombieAssociation ~= "unknown" then return true end
    end
    return false
end

return WoundEvidence
