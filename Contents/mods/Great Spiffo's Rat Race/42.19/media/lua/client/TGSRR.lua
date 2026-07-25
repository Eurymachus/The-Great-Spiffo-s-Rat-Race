require("TGSRR/Run/PendingTraitSelection")
require("TGSRR/Patches/PostDeathUI")
require("TGSRR/Outposts/Runtime")
require("TGSRR/Tracker/Window")
require("TGSRR/Run/Runtime")

if isDebugEnabled and isDebugEnabled() then
    require("TGSRR/Outposts/Debug/SurveyWindow")
end

print("[TGSRR] Client bootstrap loaded.")

Events.OnGameStart.Add(function()
    local core = getCore()
    print("[TGSRR] Context: isChallenge=" .. tostring(core and core:isChallenge())
        .. ", challengeId=" .. tostring(core and core:getChallengeID())
        .. ", gameMode=" .. tostring(core and core:getGameMode()))
end)
