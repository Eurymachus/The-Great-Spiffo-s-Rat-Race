local SelectedChallenge = require "TGSRR/Run/SelectedChallenge"

local Context = {}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

function Context.current()
    local core = getCore and getCore() or nil
    if not core or not core.getGameMode then return nil end

    local definition = SelectedChallenge.observe(core:getGameMode())
    if not definition then return nil end

    local challengeId = core.getChallengeID
        and nonEmpty(core:getChallengeID()) or nil
    if challengeId and challengeId ~= definition.id then return nil end
    return definition
end

function Context.isActive()
    return Context.current() ~= nil
end

return Context
