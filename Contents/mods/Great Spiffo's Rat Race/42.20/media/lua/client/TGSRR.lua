require("TGSRR/Run/PendingTraitSelection")
require("TGSRR/Sandbox/PresetRegistration")
require("TGSRR/Patches/PostDeathUI")
require("TGSRR/Patches/DeadSaveUI")
require("TGSRR/Animals/RanchRuntime")
require("TGSRR/Alarms/CustomDecayRuntime")
require("TGSRR/Helicopter/Runtime")
require("TGSRR/Outposts/Runtime")
require("TGSRR/Tracker/Window")
require("TGSRR/Run/Runtime")

if isDebugEnabled and isDebugEnabled() then
    require("TGSRR/Debug/HelicopterWindow")
    require("TGSRR/Debug/AlarmWindow")
    require("TGSRR/Debug/SoundWindow")
    require("TGSRR/Debug/RSLBuildingIdWindow")
    require("TGSRR/Outposts/Debug/SurveyWindow")
end

print("[TGSRR] Client bootstrap loaded.")

Events.OnGameStart.Add(function()
    if isDebugEnabled and isDebugEnabled() then
        local core = getCore()
        print("[TGSRR] Context: isChallenge=" .. tostring(core and core:isChallenge())
            .. ", challengeId=" .. tostring(core and core:getChallengeID())
            .. ", gameMode=" .. tostring(core and core:getGameMode()))
    end
end)
