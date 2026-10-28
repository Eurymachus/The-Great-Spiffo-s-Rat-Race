local root = "Contents/mods/Great Spiffo's Rat Race/42.21/media/lua/"
package.path = root .. "shared/?.lua;" .. root .. "client/?.lua;" .. package.path
package.loaded["OptionScreens/MainScreen"] = true
package.loaded["OptionScreens/LoadGameScreen"] = true
local version, mode, name, id, challenge = "42.22.0", "Sandbox", "", nil, false
local function object(value) return setmetatable({}, {__tostring=function() return value end}) end
local world = {
    getGameMode=function() return object(mode) end,
    getWorld=function() return name end,
    setWorld=function(_, value) name=value end,
}
function getWorld() return world end
function getCore() return {
    getVersionNumber=function() return version end,
    getGameMode=world.getGameMode,
    getChallengeID=function() return id end,
    isChallenge=function() return challenge end,
} end
local saves={}
local original={id="TGSRR", gameMode="The Great Spiffo's Rat Race", world="DEFAULT"}
ChallengeList={original,{id="Other", gameMode="Winter is Coming", world="DEFAULT"}}
ChallengeData={}
GameMode={SANDBOX=object("Sandbox")}
function doChallenge(c)
    assert(c.gameMode == "Challenges" or c.gameMode == "Winter is Coming", "unregistered mode")
    mode=c.gameMode; id=c.id; challenge=true; name="random"
end
function createWorld(value) name=value; saves[mode .. "/" .. name]={gameMode=mode,saveName=name,playerAlive=true} end
world.setGameMode=function(_, value) mode=tostring(value) end
MainScreen={instance={setDefaultSandboxVars=function() end}}
function MainScreen.continueLatestSaveAux()
    assert(saves[mode .. "/" .. name], "save path mismatch")
end
-- Execute the installed vanilla Continue implementation, not a test copy.
local f=assert(io.open("C:/Games/Steam/steamapps/common/ProjectZomboid/media/lua/client/OptionScreens/MainScreen.lua"))
local source=f:read("*a"); f:close()
local start=assert(source:find("MainScreen.continueLatestSave = function",1,true))
local finish=assert(source:find("MainScreen.onMenuItemMouseDownMainMenu =",start,true))
assert(loadstring(source:sub(start,finish-1)))()
LoadGameScreen={getChallenge=function(_, item)
    for _,c in ipairs(ChallengeList) do if c.gameMode==item.gameMode then return c end end
end}
local Selected=require("TGSRR/Run/SelectedChallenge")
Selected.register(original)
local Context=require("TGSRR/Challenge/Context")
require("TGSRR/Patches/OfficialMode")
-- Match NewGameScreen: doChallenge is followed by setWorld and createWorld.
doChallenge(original); world:setWorld("12345"); createWorld("12345")
assert(mode=="Challenges" and name=="TGSRR_12345")
assert(original.gameMode=="The Great Spiffo's Rat Race")
assert(Context.current().id=="TGSRR")
assert(Context.current().gameMode==original.gameMode)
id=nil; challenge=false
assert(Context.current().id=="TGSRR", "identity survives cleared transient state")
mode="Sandbox"; name="other"
MainScreen.continueLatestSave("Challenges","TGSRR_12345")
assert(mode=="Challenges" and name=="TGSRR_12345" and id=="TGSRR")
assert(ChallengeData.chosenChallenge==original)
assert(LoadGameScreen:getChallenge(saves[mode .. "/" .. name])==original)
assert(LoadGameScreen:getChallenge({gameMode="Challenges",saveName="other"})==nil)
name="other"; assert(Context.current()==nil)
-- Ordinary Sandbox and other challenge saves retain their vanilla routing.
saves["Sandbox/ordinary"]={}; MainScreen.continueLatestSave("Sandbox","ordinary")
assert(mode=="Sandbox" and name=="ordinary")
saves["Winter is Coming/other"]={}; MainScreen.continueLatestSave("Winter is Coming","other")
assert(mode=="Winter is Coming" and id=="Other")
-- Dead-save policy covers the new folder convention.
SaveInfoPanel=nil; ConfigPanel=nil; LoadGameScreen.disableBtn=function() end
function getFileSeparator() return "/" end
function getSaveInfo(path) return saves[path] end
MainScreen.startNormalMainScreen=function() end
require("TGSRR/Patches/DeadSaveUI")
saves["Challenges/TGSRR_12345"].playerAlive=false
MainScreen.continueLatestSave("Challenges","TGSRR_12345")
assert(mode=="Winter is Coming", "dead official save must not load")
-- Requiring the patch again cannot wrap it twice.
package.loaded["TGSRR/Patches/OfficialMode"]=nil
require("TGSRR/Patches/OfficialMode")
version="42.21.0"; assert(require("TGSRR/Challenge/OfficialMode").enabled()==false)
print("42.22 official mode tests passed")
