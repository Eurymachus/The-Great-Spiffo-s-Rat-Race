local EventCodec = require "TGSRR/Run/EventCodec"
local CharacterSnapshot = require "TGSRR/Run/CharacterSnapshot"

local PendingTraitSelection = {}

local FILE = "TGSRR/pending-trait-selection"
local MAX_AGE_SECONDS = 24 * 60 * 60

local function hexEncode(value)
    return (tostring(value or ""):gsub(".", function(character)
        return string.format("%02x", string.byte(character))
    end))
end

local function hexDecode(value)
    value = tostring(value or "")
    if #value % 2 ~= 0 or value:find("[^0-9a-f]") then return nil end
    return (value:gsub("..", function(pair) return string.char(tonumber(pair, 16)) end))
end

local function write(value)
    if createFolder then createFolder("TGSRR") end
    local writer = getFileWriter and getFileWriter(FILE, true, false) or nil
    if not writer then return false end
    writer:write(value or "")
    writer:close()
    return true
end

local function read()
    local reader = getFileReader and getFileReader(FILE, true) or nil
    if not reader then return nil end
    local lines = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        lines[#lines + 1] = line
    end
    reader:close()
    if #lines == 0 then return nil end
    local canonical = hexDecode(table.concat(lines))
    if not canonical then return nil end
    return EventCodec.decodePayload(canonical)
end

local function traitId(item)
    if not item then return nil end
    if item.getType then
        local value = item:getType()
        if value ~= nil then return tostring(value) end
    end
    return type(item) == "string" and item or tostring(item)
end

local function selectedTraits()
    local profession = CharacterCreationProfession and CharacterCreationProfession.instance or nil
    local list = profession and profession.listboxTraitSelected or nil
    local values = {}
    for _, entry in ipairs(list and list.items or {}) do
        local value = traitId(entry and entry.item)
        if value and value ~= "" then values[#values + 1] = value end
    end
    return CharacterSnapshot.normalizeTraitIds(values)
end

function PendingTraitSelection.capture(screen)
    local descriptor = MainScreen and MainScreen.instance and MainScreen.instance.desc or nil
    if not descriptor then return false end
    local character = CharacterSnapshot.nameFromValues(
        screen and screen.forenameEntry and screen.forenameEntry:getText()
            or descriptor:getForename(),
        screen and screen.surnameEntry and screen.surnameEntry:getText()
            or descriptor:getSurname()
    )
    local canonical, encodeError = EventCodec.canonicalPayload({
        schema = 1,
        capturedUtc = math.floor(tonumber(os.time()) or 0),
        character = character,
        selectedTraits = selectedTraits(),
    })
    if not canonical then
        print("[TGSRR Run] Unable to capture selected traits: " .. tostring(encodeError))
        return false
    end
    return write(hexEncode(canonical))
end

function PendingTraitSelection.consume(player)
    local pending = read()
    if type(pending) ~= "table" or tonumber(pending.schema) ~= 1 then return nil end
    local capturedUtc = tonumber(pending.capturedUtc) or 0
    local age = math.floor(tonumber(os.time()) or 0) - capturedUtc
    local current = CharacterSnapshot.name(player)
    local pendingName = type(pending.character) == "table" and pending.character or {}
    if age < 0 or age > MAX_AGE_SECONDS
            or tostring(pendingName.forename or "") ~= current.forename
            or tostring(pendingName.surname or "") ~= current.surname then
        return nil
    end
    write("")
    return {
        capturedUtc = capturedUtc,
        traits = CharacterSnapshot.normalizeTraitIds(pending.selectedTraits),
    }
end

function PendingTraitSelection.install()
    if not CharacterCreationMain or CharacterCreationMain._tgsrrTraitSelectionHooked then return end
    CharacterCreationMain._tgsrrTraitSelectionHooked = true
    local previousCreate = CharacterCreationMain.create
    CharacterCreationMain.create = function(self, ...)
        if previousCreate then previousCreate(self, ...) end
        local button = self.playButton
        if not button or button._tgsrrTraitSelectionHooked then return end
        button._tgsrrTraitSelectionHooked = true
        local previousMouseUp = button.onMouseUp
        button.onMouseUp = function(clicked, x, y)
            PendingTraitSelection.capture(self)
            if previousMouseUp then return previousMouseUp(clicked, x, y) end
        end
    end
end

PendingTraitSelection.install()

return PendingTraitSelection
