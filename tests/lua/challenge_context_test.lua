local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

local gameMode = "Sandbox"
local challenge = false
local challengeId = ""

function getCore()
    return {
        getGameMode = function() return gameMode end,
        isChallenge = function() return challenge end,
        getChallengeID = function() return challengeId end,
    }
end

local SelectedChallenge = require "TGSRR/Run/SelectedChallenge"
SelectedChallenge.register({
    id = "TGSRR",
    gameMode = "The Great Spiffo's Rat Race",
})

local Context = require "TGSRR/Challenge/Context"
assert(Context.isActive() == false)

gameMode = "The Great Spiffo's Rat Race"
assert(Context.isActive() == false)

challenge = true
challengeId = "TGSRR"
assert(Context.isActive() == true)

challengeId = "OtherChallenge"
assert(Context.isActive() == false)

gameMode = "Sandbox"
challengeId = "TGSRR"
assert(Context.isActive() == false)

print("challenge context test passed")
