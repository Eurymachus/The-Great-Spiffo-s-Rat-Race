local CharacterSnapshot = {}

local function nonEmpty(value)
    if value == nil then return nil end
    value = tostring(value)
    if value == "" then return nil end
    return value
end

local function sortedUnique(values)
    local result, seen = {}, {}
    for _, value in ipairs(values or {}) do
        value = nonEmpty(value)
        if value and not seen[value] then
            seen[value] = true
            result[#result + 1] = value
        end
    end
    table.sort(result)
    return result
end

function CharacterSnapshot.normalizeTraitIds(values)
    return sortedUnique(values)
end

function CharacterSnapshot.nameFromValues(forename, surname)
    forename = nonEmpty(forename) or "Unknown"
    surname = nonEmpty(surname) or ""
    local displayName = forename
    if surname ~= "" then displayName = displayName .. " " .. surname end
    return {
        forename = forename,
        surname = surname,
        displayName = displayName,
    }
end

function CharacterSnapshot.name(player)
    local descriptor = player and player.getDescriptor and player:getDescriptor() or nil
    return CharacterSnapshot.nameFromValues(
        descriptor and descriptor:getForename(),
        descriptor and descriptor:getSurname()
    )
end

function CharacterSnapshot.traits(player)
    local result = {}
    local characterTraits = player and player.getCharacterTraits
        and player:getCharacterTraits() or nil
    local knownTraits = characterTraits and characterTraits.getKnownTraits
        and characterTraits:getKnownTraits() or nil
    if knownTraits then
        for index = 0, knownTraits:size() - 1 do
            result[#result + 1] = tostring(knownTraits:get(index))
        end
    elseif player and player.getTraits then
        -- Compatibility for older pre-release Build 42 saves.
        local traits = player:getTraits()
        if traits then
            for index = 0, traits:size() - 1 do
                result[#result + 1] = tostring(traits:get(index))
            end
        end
    end
    return sortedUnique(result)
end

function CharacterSnapshot.observe(player)
    return {
        name = CharacterSnapshot.name(player),
        traits = CharacterSnapshot.traits(player),
    }
end

return CharacterSnapshot
