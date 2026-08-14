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

function CharacterSnapshot.professionId(player)
    local descriptor = player and player.getDescriptor
        and player:getDescriptor() or nil
    local profession = descriptor and descriptor.getCharacterProfession
        and descriptor:getCharacterProfession() or nil
    local id = profession and profession.getName
        and profession:getName() or nil
    return nonEmpty(id) or ""
end

function CharacterSnapshot.identity(player)
    local result = CharacterSnapshot.name(player)
    result.professionId = CharacterSnapshot.professionId(player)
    return result
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
    end
    return sortedUnique(result)
end

function CharacterSnapshot.observe(player)
    return {
        identity = CharacterSnapshot.identity(player),
        traits = CharacterSnapshot.traits(player),
    }
end

return CharacterSnapshot
