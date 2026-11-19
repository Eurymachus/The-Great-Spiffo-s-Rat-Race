local root = "Contents/mods/Great Spiffo's Rat Race/42.22/media/lua/"
package.path = root .. "client/?.lua;" .. package.path
package.loaded["OptionScreens/NewGameScreen"] = true
local function read(path)
    local file = assert(io.open(path))
    local source = file:read("*a")
    file:close()
    return source
end
local source = read("C:/Games/Steam/steamapps/common/ProjectZomboid/media/lua/client/OptionScreens/NewGameScreen.lua")
local first = assert(source:find("function NewGameScreen:clickPlay()", 1, true))
local last = assert(source:find("function NewGameScreen:onGainJoypadFocus", first, true))
NewGameScreen = {}
assert(loadstring(source:sub(first, last - 1)))()
local mode = "Challenges"
GameMode = { CHALLENGES = { toString = function() return "Challenges" end } }
local world = { setGameMode = function(_, value) mode = value end,
    setWorld = function(_, value) worldName = value end }
function getWorld() return world end
function ZombRand() return 1 end
ChallengeData = {}
local initialized, created, defaults, saved, filled = 0, 0, 0, 0, 0
function doChallenge(challenge) initialized = initialized + 1 end
function createWorld(name) created = created + 1 end
local profession = { setVisible = function(self, visible) self.visible = visible end }
MainScreen = { instance = { charCreationProfession = profession,
    setDefaultSandboxVars = function() end } }
local spawn = {
    choices = true,
    hasChoices = function(self) return self.choices end,
    useDefaultSpawnRegion = function() defaults = defaults + 1 end,
    saveGenParams = function() saved = saved + 1 end,
    fillList = function() filled = filled + 1 end,
    setVisible = function(self, visible, focus) self.visible = visible; self.focus = focus end,
}
MapSpawnSelect = { instance = spawn }
WorldSelect = { instance = {} }
local screen = setmetatable({ inChallengesView = true, joyfocus = {},
    setVisible = function() end }, { __index = NewGameScreen })
local function play(id, choices, arrow)
    spawn.visible = false; profession.visible = false; spawn.choices = choices
    screen.selectedItem = { data = { mode = mode, challenge = { id = id }, arrowButton = arrow } }
    screen:clickPlay()
end
-- Reproduce the installed vanilla bypass before applying the patch.
play("TGSRR", true)
assert(profession.visible and not spawn.visible)
require("TGSRR/Patches/SpawnSelection")
for _, id in ipairs({"TGSRR", "TGSRR_CDDA", "TGSRR_Sprinters"}) do
    local before = initialized
    play(id, true)
    assert(initialized == before + 1, "challenge must initialize exactly once")
    assert(spawn.visible and not profession.visible)
    assert(spawn.previousScreen == "NewGameScreen" and spawn.focus == screen.joyfocus)
    assert(ChallengeData.chosenChallenge.id == id)
end
play("OtherChallenge", true)
assert(profession.visible and not spawn.visible)
play("TGSRR", false)
assert(profession.visible and not spawn.visible)
local before = initialized
play("TGSRR", true, true)
assert(initialized == before and not spawn.visible)
assert(created == initialized and defaults == initialized and saved == initialized)
assert(filled == 3)
local patched = NewGameScreen.clickPlay
package.loaded["TGSRR/Patches/SpawnSelection"] = nil
require("TGSRR/Patches/SpawnSelection")
assert(NewGameScreen.clickPlay == patched)
print("42.22 spawn selection tests passed")
