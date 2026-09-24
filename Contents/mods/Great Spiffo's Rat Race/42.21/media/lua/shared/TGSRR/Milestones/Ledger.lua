local Ledger = {}
local MOD_DATA_KEY = "TGSRR_MilestoneLedger"
local SCHEMA_VERSION = 1

local function root()
    local data = ModData.getOrCreate(MOD_DATA_KEY)
    if data.schemaVersion ~= SCHEMA_VERSION then
        data.schemaVersion = SCHEMA_VERSION
        data.claims = {}
    elseif type(data.claims) ~= "table" then
        data.claims = {}
    end
    return data
end

function Ledger.isClaimed(key)
    return key and root().claims[key] ~= nil or false
end

function Ledger.claim(key, details)
    if not key or Ledger.isClaimed(key) then return false end
    local gameTime = getGameTime()
    root().claims[key] = {
        claimedAt = gameTime and gameTime:getWorldAgeHours() or nil,
        details = details,
    }
    return true
end

function Ledger.getClaims()
    return root().claims
end

return Ledger
