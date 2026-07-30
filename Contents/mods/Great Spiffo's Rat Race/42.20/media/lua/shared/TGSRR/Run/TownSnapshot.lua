local Towns = require "TGSRR/Towns/Definitions"

local TownSnapshot = {}

local function visitSnapshot(visit)
    if type(visit) ~= "table" then return nil end
    return {
        utc = math.max(0, math.floor(tonumber(visit.utc) or 0)),
        worldAgeHours = math.max(0, tonumber(visit.worldAgeHours) or 0),
        pointId = tostring(visit.pointId or ""),
        x = math.floor(tonumber(visit.x) or 0),
        y = math.floor(tonumber(visit.y) or 0),
    }
end

function TownSnapshot.observe(run)
    local visits = type(run) == "table" and run.townVisits or {}
    local result = {}
    for _, town in ipairs(Towns.getAll()) do
        local visit = visitSnapshot(visits and visits[town.id])
        result[#result + 1] = {
            id = town.id,
            visited = visit ~= nil,
            firstVisit = visit,
        }
    end
    return {
        partial = type(run) == "table" and run.townVisitsPartial == true,
        towns = result,
    }
end

return TownSnapshot
