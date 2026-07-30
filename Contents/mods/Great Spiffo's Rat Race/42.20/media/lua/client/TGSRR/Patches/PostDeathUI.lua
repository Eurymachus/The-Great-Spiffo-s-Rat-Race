require "ISUI/ISPostDeathUI"

local Identity = require "TGSRR/Run/Identity"

local function TGSRR_isRatRaceChallenge()
    return Identity.isRatRaceChallenge()
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
