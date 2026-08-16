local EventCodec = require "TGSRR/Run/EventCodec"
local CharacterSnapshot = require "TGSRR/Run/CharacterSnapshot"

local PendingTraitSelection = {}

local FILE = "TGSRR/pending-trait-selection.txt"
local MAX_AGE_SECONDS = 24 * 60 * 60
local RANDOM_PENDING_NAME = "__TGSRR_RANDOM_PENDING__"

local CHALLENGE_IDS = {
    TGSRR = true,
    TGSRR_CDDA = true,
    TGSRR_Sprinters = true,
}

local function isRatRaceChallenge()
    local core = getCore and getCore() or nil
    if not core then return false end
    local id = core.getChallengeID and tostring(core:getChallengeID() or "") or ""
    if CHALLENGE_IDS[id] then return true end
    local mode = core.getGameMode and tostring(core:getGameMode() or "") or ""
    return mode == "The Great Spiffo's Rat Race"
        or mode == "The Great Spiffo's Rat Race - CDDA"
        or mode == "The Great Spiffo's Rat Race - Sprinters"
end

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

local function randomCandidates(screen)
    local candidates = {}
    for _, entry in ipairs(screen and screen.listbox
            and screen.listbox.items or {}) do
        local item = entry and entry.item or nil
        if item and not item._tgsrrRandom and type(item.region) == "table"
                and item.region.name then
            candidates[#candidates + 1] = item.region
        end
    end
    return candidates
end

local function resolveChosenStartingRegion()
    if not isRatRaceChallenge() then return nil end
    local screen = MapSpawnSelect and MapSpawnSelect.instance or nil
    if not screen then return nil end
    local pending = screen._tgsrrPendingRandomRegion
    local mode = "explicit"
    if type(pending) == "table" then
        mode = "random"
        if type(pending.resolved) ~= "table" then
            local candidates = pending.candidates or {}
            if #candidates == 0 then return nil end
            pending.resolved = candidates[ZombRand(#candidates) + 1]
        end
        screen.selectedRegion = pending.resolved
        setSpawnRegion(screen.selectedRegion.name)
        getCore():setSelectedMap(tostring(screen.selectedRegion.name))
    end
    local region = screen.selectedRegion
    if type(region) ~= "table" or not region.name then return nil end
    return {
        schema = 1,
        selectionMode = mode,
        resolvedRegionId = tostring(region.name),
    }
end

function PendingTraitSelection.capture(screen)
    local chosenStartingRegion = resolveChosenStartingRegion()
    local descriptor = MainScreen and MainScreen.instance and MainScreen.instance.desc or nil
    if not descriptor then return false end
    local capturedUtc = math.floor(tonumber(os.time()) or 0)
    local character = CharacterSnapshot.nameFromValues(
        screen and screen.forenameEntry and screen.forenameEntry:getText()
            or descriptor:getForename(),
        screen and screen.surnameEntry and screen.surnameEntry:getText()
            or descriptor:getSurname()
    )
    local canonical, encodeError = EventCodec.canonicalPayload({
        schema = 2,
        capturedUtc = capturedUtc,
        character = character,
        selectedTraits = selectedTraits(),
        chosenStartingRegion = chosenStartingRegion and {
            schema = chosenStartingRegion.schema,
            selectionMode = chosenStartingRegion.selectionMode,
            resolvedRegionId = chosenStartingRegion.resolvedRegionId,
            capturedUtc = capturedUtc,
        } or nil,
    })
    if not canonical then
        print("[TGSRR Run] Unable to capture selected traits: " .. tostring(encodeError))
        return false
    end
    return write(hexEncode(canonical))
end

function PendingTraitSelection.consume(player)
    local pending = read()
    if type(pending) ~= "table" or tonumber(pending.schema) ~= 2 then return nil end
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
        chosenStartingRegion = type(pending.chosenStartingRegion) == "table"
            and pending.chosenStartingRegion or nil,
    }
end

local function installSpawnSelectionHook()
    if not MapSpawnSelect or MapSpawnSelect._tgsrrBlindRandomHooked then return end
    MapSpawnSelect._tgsrrBlindRandomHooked = true
    local previousRender = MapSpawnSelect.render
    if previousRender then
        MapSpawnSelect.render = function(self, ...)
            local previousSelectedMapIndex = self.selectedMapIndex
            local entry = self.listbox and self.listbox.items
                and self.listbox.items[self.listbox.selected] or nil
            local item = entry and entry.item or nil
            local result = previousRender(self, ...)
            if item and item._tgsrrRandom
                    and previousSelectedMapIndex ~= self.listbox.selected
                    and self.mapPanel and self.mapPanel.mapAPI
                    and self.mapPanel.mapAPI.resetView then
                self.mapPanel.mapAPI:resetView()
            end
            return result
        end
    end
    local previousClickNext = MapSpawnSelect.clickNext
    MapSpawnSelect.clickNext = function(self, ...)
        local entry = self.listbox and self.listbox.items
            and self.listbox.items[self.listbox.selected] or nil
        local item = entry and entry.item or nil
        if not isRatRaceChallenge() or not item or not item._tgsrrRandom then
            self._tgsrrPendingRandomRegion = nil
            return previousClickNext(self, ...)
        end
        local candidates = randomCandidates(self)
        if #candidates == 0 then return previousClickNext(self, ...) end
        self._tgsrrPendingRandomRegion = {
            candidates = candidates,
        }
        local originalName = item.name
        local originalRegion = item.region
        item.name = RANDOM_PENDING_NAME
        item.region = candidates[1]
        local result = previousClickNext(self, ...)
        item.name = originalName
        item.region = originalRegion
        return result
    end
end

function PendingTraitSelection.install()
    installSpawnSelectionHook()
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
