local Deliverables = require "TGSRR/Challenge/Deliverables"

local ChallengeProgressSnapshot = {}

local RULES_VERSION = 1

function ChallengeProgressSnapshot.observe(player)
    local context = { player = player }
    Deliverables.refreshAll(context)
    local categories = {}
    for _, record in ipairs(Deliverables.getAll(context)) do
        categories[record.id] = {
            available = record.available ~= false,
            current = tonumber(record.current) or 0,
            target = tonumber(record.target) or 0,
            progress = math.max(0, math.min(1,
                (tonumber(record.percent) or 0) / 100)),
            status = record.status and tostring(record.status) or nil,
        }
    end
    return {
        rulesVersion = RULES_VERSION,
        categories = categories,
    }
end

return ChallengeProgressSnapshot
