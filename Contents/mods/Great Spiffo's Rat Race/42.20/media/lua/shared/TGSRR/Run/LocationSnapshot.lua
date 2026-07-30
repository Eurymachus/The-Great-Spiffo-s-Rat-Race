local Locations = require "TGSRR/Locations/Definitions"

local LocationSnapshot = {}

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

function LocationSnapshot.observe(run)
    local state = type(run) == "table" and run.locations or nil
    local visits = state and state.visits or {}
    local entries = {}
    for _, location in ipairs(Locations.getAll()) do
        local visit = visitSnapshot(visits[location.id])
        entries[#entries + 1] = {
            id = location.id,
            visited = visit ~= nil,
            firstVisit = visit,
        }
    end
    return {
        schema = 1,
        registryVersion = Locations.getVersion(),
        partial = not state or state.partial == true,
        entries = entries,
    }
end

return LocationSnapshot
