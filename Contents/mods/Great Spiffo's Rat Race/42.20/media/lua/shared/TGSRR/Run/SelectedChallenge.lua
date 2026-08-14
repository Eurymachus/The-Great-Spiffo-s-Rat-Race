local SelectedChallenge = {}

local definitionsByGameMode = {}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

function SelectedChallenge.register(definition)
    if type(definition) ~= "table" then return false end
    local id = nonEmpty(definition.id)
    local gameMode = nonEmpty(definition.gameMode)
    if not id or not gameMode then return false end

    local existing = definitionsByGameMode[gameMode]
    if existing and existing.id ~= id then
        error("TGSRR challenge game mode collision: " .. gameMode)
    end
    definitionsByGameMode[gameMode] = {
        id = id,
        gameMode = gameMode,
    }
    return true
end

function SelectedChallenge.observe(gameMode)
    gameMode = nonEmpty(gameMode)
    if not gameMode then return nil end
    local evidence = definitionsByGameMode[gameMode]
    if not evidence then
        return nil
    end
    return {
        id = evidence.id,
        gameMode = evidence.gameMode,
    }
end

return SelectedChallenge
