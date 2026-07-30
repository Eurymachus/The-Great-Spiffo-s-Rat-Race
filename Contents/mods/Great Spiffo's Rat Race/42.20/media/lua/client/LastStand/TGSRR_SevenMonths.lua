local Challenge = {}

local TGSRR_SandboxBase = require("TGSRR/Sandbox/Base")
local TGSRR_SelectedChallenge = require("TGSRR/Run/SelectedChallenge")

Challenge.id = "TGSRR_SevenMonths"
Challenge.completionText =
    "Seven-month ranch-spawn test variant."
Challenge.image = "media/lua/client/LastStand/outpostmap.png"
Challenge.gameMode =
    "The Great Spiffo's Rat Race - Seven Months Later (Test)"
Challenge.world = "DEFAULT"
TGSRR_SelectedChallenge.register(Challenge)

Challenge.Add = function()
    addChallenge(Challenge)
end

Challenge.getSpawnRegion = function()
    local regions = {}

    for _, dir in ipairs(getMapDirectoryTable()) do
        local file = "media/maps/" .. dir .. "/spawnpoints.lua"

        if fileExists(file) then
            table.insert(regions, {
                name = dir,
                file = file,
            })
        end
    end

    return SpawnRegionMgr.loadSpawnRegions(regions)
end

Challenge.OnInitWorld = function()
    TGSRR_SandboxBase.apply()

    -- Enum value 8 represents (8 - 1) * 30 = 210 elapsed days.
    SandboxVars.TimeSinceApo = 8

    Events.OnGameStart.Add(Challenge.OnGameStart)
end

Challenge.OnGameStart = function()
end

Challenge.AddPlayer = function()
end

Challenge.RemovePlayer = function()
end

Challenge.Render = function()
end

Events.OnChallengeQuery.Add(Challenge.Add)

return Challenge
