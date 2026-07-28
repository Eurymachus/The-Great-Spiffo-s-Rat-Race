package.loaded["TGSRR/Run/CharacterSnapshot"] = {
    identity = function() return {} end,
    traits = function() return {} end,
}

ModData = {
    getOrCreate = function() return {} end,
}

local liveChallengeId = ""
local liveGameMode = "The Great Spiffo's Rat Race - CDDA"
getCore = function()
    return {
        getChallengeID = function() return liveChallengeId end,
        getGameMode = function() return liveGameMode end,
    }
end

LastStandData = {
    chosenChallenge = {
        id = "TGSRR_CDDA",
        gameMode = "The Great Spiffo's Rat Race - CDDA",
    },
}

local SelectedChallenge = require "TGSRR/Run/SelectedChallenge"
local Identity = require "TGSRR/Run/Identity"

assert(SelectedChallenge.register(LastStandData.chosenChallenge))
LastStandData.chosenChallenge = nil
local selected = Identity.observeChallenge()
assert(selected.id == "TGSRR_CDDA")
assert(selected.gameMode == liveGameMode)
assert(Identity.isRatRaceChallenge() == true)

liveGameMode = "Different mode"
local mismatched = Identity.observeChallenge()
assert(mismatched.id == "")

liveChallengeId = "TGSRR_CDDA"
local engineFallback = Identity.observeChallenge()
assert(engineFallback.id == "TGSRR_CDDA")

print("challenge evidence test passed")
