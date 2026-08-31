local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local encodedPayload = nil
package.loaded["TGSRR/Run/EventCodec"] = {
    canonicalPayload = function(value)
        encodedPayload = value
        return "x"
    end,
    decodePayload = function() return nil end,
}
package.loaded["TGSRR/Run/CharacterSnapshot"] = {
    nameFromValues = function(forename, surname)
        return { forename = forename, surname = surname }
    end,
    normalizeTraitIds = function(values) return values or {} end,
}

local selectedMap = nil
local spawnRegion = nil
local resetViewCount = 0
local challengeID = "TGSRR"
local gameMode = "The Great Spiffo's Rat Race"
getCore = function()
    return {
        getChallengeID = function() return challengeID end,
        getGameMode = function() return gameMode end,
        setSelectedMap = function(_, value) selectedMap = value end,
    }
end
setSpawnRegion = function(value) spawnRegion = value end
ZombRand = function(count)
    assert(count == 2)
    return 1
end
getText = function() return "Random" end
createFolder = function() end
getFileWriter = function()
    return {
        write = function() end,
        close = function() end,
    }
end

MapSpawnSelect = {
    render = function(self)
        self.selectedMapIndex = self.listbox.selected
    end,
    clickNext = function(self)
        local item = self.listbox.items[self.listbox.selected].item
        self.selectedRegion = item.region
        setSpawnRegion(self.selectedRegion.name)
        getCore():setSelectedMap(self.selectedRegion.name)
    end,
}

local previousFinalClick = false
CharacterCreationMain = {
    create = function(self)
        self.playButton = {
            onMouseUp = function()
                previousFinalClick = true
            end,
        }
    end,
}
CharacterCreationProfession = {
    instance = {
        listboxTraitSelected = { items = {} },
    },
}
MainScreen = {
    instance = {
        desc = {
            getForename = function() return "Test" end,
            getSurname = function() return "Rat" end,
        },
    },
}

require "TGSRR/Run/PendingTraitSelection"

local randomItem = {
    name = "Random",
    region = nil,
    _tgsrrRandom = true,
}
local muldraugh = { name = "Muldraugh, KY", points = {} }
local rosewood = { name = "Rosewood, KY", points = {} }
local spawnScreen = {
    selectedMapIndex = 2,
    mapPanel = {
        mapAPI = {
            resetView = function()
                resetViewCount = resetViewCount + 1
            end,
        },
    },
    listbox = {
        selected = 1,
        items = {
            { item = randomItem },
            { item = { name = "Muldraugh", region = muldraugh } },
            { item = { name = "Rosewood", region = rosewood } },
        },
    },
}
MapSpawnSelect.instance = spawnScreen

MapSpawnSelect.render(spawnScreen)
assert(resetViewCount == 1)
MapSpawnSelect.clickNext(spawnScreen)
assert(spawnScreen.selectedRegion == muldraugh)
assert(spawnScreen.listbox.selected == 1)
assert(spawnScreen._tgsrrPendingRandomRegion.resolved == nil)

local creationScreen = {
    forenameEntry = { getText = function() return "Test" end },
    surnameEntry = { getText = function() return "Rat" end },
}
CharacterCreationMain.create(creationScreen)
creationScreen.playButton.onMouseUp(creationScreen.playButton, 0, 0)

assert(previousFinalClick == true)
assert(spawnScreen.selectedRegion == rosewood)
assert(spawnRegion == "Rosewood, KY")
assert(selectedMap == "Rosewood, KY")
assert(encodedPayload.schema == 2)
assert(encodedPayload.chosenStartingRegion.selectionMode == "random")
assert(encodedPayload.chosenStartingRegion.resolvedRegionId == "Rosewood, KY")
assert(type(encodedPayload.chosenStartingRegion.capturedUtc) == "number")

challengeID = ""
gameMode = "Sandbox"
spawnScreen._tgsrrPendingRandomRegion = { candidates = { muldraugh, rosewood } }
spawnScreen.selectedRegion = nil
MapSpawnSelect.clickNext(spawnScreen)
assert(spawnScreen.selectedRegion == rosewood)
assert(spawnScreen._tgsrrPendingRandomRegion == nil)
assert(spawnRegion == "Rosewood, KY")
assert(selectedMap == "Rosewood, KY")

print("pending starting region test passed")
