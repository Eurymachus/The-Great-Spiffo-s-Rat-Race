local gameStartHandler = nil
local challengeQueryHandler = nil
local addedChallenge = nil
local baseApplied = false

package.loaded["LastStand/TGSRR_SandboxBase"] = {
    apply = function()
        baseApplied = true
        SandboxVars.TimeSinceApo = 1
    end,
}

SandboxVars = {}
Events = {
    OnChallengeQuery = {
        Add = function(handler) challengeQueryHandler = handler end,
    },
    OnGameStart = {
        Add = function(handler) gameStartHandler = handler end,
    },
}

function addChallenge(challenge)
    addedChallenge = challenge
end

local Challenge = require "LastStand/TGSRR_SevenMonths"

assert(challengeQueryHandler == Challenge.Add)
challengeQueryHandler()
assert(addedChallenge == Challenge)
assert(Challenge.id == "TGSRR_SevenMonths")
assert(Challenge.gameMode ==
    "The Great Spiffo's Rat Race - Seven Months Later (Test)")

Challenge.OnInitWorld()
assert(baseApplied == true)
assert(SandboxVars.TimeSinceApo == 8)
assert((SandboxVars.TimeSinceApo - 1) * 30 == 210)
assert(gameStartHandler == Challenge.OnGameStart)

print("seven month challenge test passed")
