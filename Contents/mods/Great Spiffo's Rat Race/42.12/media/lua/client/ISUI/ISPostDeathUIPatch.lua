require "ISUI/ISPostDeathUI"

local TGSRR_CHALLENGE_IDS = {
    TGSRR = true,
    TGSRR_CDDA = true,
    TGSRR_Sprinters = true
}

local function TGSRR_isRatRaceChallenge()
    return getCore():isChallenge() and TGSRR_CHALLENGE_IDS[getCore():getChallengeID()] == true
end

if ISPostDeathUI and not ISPostDeathUI.TGSRR_postDeathPatched then
    local postDeathUICreateChildren = ISPostDeathUI.createChildren

    function ISPostDeathUI:createChildren()
        postDeathUICreateChildren(self)

        if TGSRR_isRatRaceChallenge() and self.buttonRespawn then
            self.buttonRespawn:setVisible(false)
            self:removeChild(self.buttonRespawn)
        end
    end

    ISPostDeathUI.TGSRR_postDeathPatched = true
end
