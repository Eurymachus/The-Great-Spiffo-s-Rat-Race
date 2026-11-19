-- Temporary diagnostic requested for the 2.0 development mod. Remove before release.
require("Challenge/WinterIsComing")
require("OptionScreens/ChallengeList")

local modeName = "TGSRR:test"
local challengeId = "TGSRRGameModeSaveProbe"
local function log(message)
    print("[TGSRR Save Probe] " .. message)
end

local location = ResourceLocation.of(modeName)
local mode = GameMode.get(location)
if not mode then
    log("Registering " .. modeName)
    mode = GameMode.register(modeName, false)
end
log("Registry lookup: " .. tostring(GameMode.get(location)))

-- Clone the known vanilla challenge, leaving its original definition intact.
local challenge = {}
for key, value in pairs(WinterIsComing) do
    challenge[key] = value
end
challenge.id = challengeId
challenge.gameMode = modeName
challenge.Add = function()
    addChallenge(challenge)
    challenge.name = "TGSRR:test - Save Path Probe"
    challenge.description = "Temporary save-path test using Winter is Coming. Registers TGSRR:test directly, without Rat Race save routing. This test may fail to create a save."
end
Events.OnChallengeQuery.Add(challenge.Add)

local originalCreateWorld = createWorld
function createWorld(name)
    if getCore():getChallengeID() ~= challengeId then
        return originalCreateWorld(name)
    end
    log("Before createWorld: mode=" .. tostring(getCore():getGameMode())
        .. ", world=" .. tostring(name))
    originalCreateWorld(name)
    log("createWorld returned: mode=" .. tostring(getCore():getGameMode())
        .. ", world=" .. tostring(getWorld():getWorld()))
end

Events.OnGameStart.Add(function()
    if getCore():getChallengeID() == challengeId then
        log("Reached OnGameStart: mode=" .. tostring(getCore():getGameMode())
            .. ", world=" .. tostring(getWorld():getWorld()))
    end
end)
