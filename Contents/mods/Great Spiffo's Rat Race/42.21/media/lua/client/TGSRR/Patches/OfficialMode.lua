require("OptionScreens/MainScreen")
require("OptionScreens/LoadGameScreen")
local OfficialMode = require("TGSRR/Challenge/OfficialMode")

if not OfficialMode.enabled() then return end
if MainScreen.TGSRR_officialModePatched then return end

-- Keep the challenge definition and exported identity distinct from its storage
-- mode. Custom namespaced modes currently produce invalid Windows save paths.
local originalDoChallenge = doChallenge
function doChallenge(challenge)
    if challenge.id ~= "TGSRR" then return originalDoChallenge(challenge) end
    return originalDoChallenge({
        id = challenge.id,
        gameMode = OfficialMode.storage,
        world = challenge.world,
    })
end

local originalCreateWorld = createWorld
function createWorld(name)
    local core = getCore()
    if core:isChallenge() and core:getChallengeID() == "TGSRR"
            and tostring(core:getGameMode()) == OfficialMode.storage then
        if not OfficialMode.isSave(OfficialMode.storage, name) then
            name = OfficialMode.prefix .. tostring(name)
        end
    end
    return originalCreateWorld(name)
end

local continueLatestSave = MainScreen.continueLatestSave
function MainScreen.continueLatestSave(mode, name)
    if OfficialMode.isSave(mode, name) then
        -- Vanilla still finds the original challenge definition and initializes
        -- its ID, sandbox settings and callbacks through doChallenge above.
        return continueLatestSave(OfficialMode.legacy, name)
    end
    return continueLatestSave(mode, name)
end

local getChallenge = LoadGameScreen.getChallenge
function LoadGameScreen:getChallenge(item)
    if OfficialMode.isSave(item.gameMode, item.saveName) then
        for _, challenge in ipairs(ChallengeList) do
            if challenge.id == "TGSRR" then return challenge end
        end
        return nil
    end
    return getChallenge(self, item)
end

MainScreen.TGSRR_officialModePatched = true
