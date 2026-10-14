package.path = "Contents/mods/Great Spiffo's Rat Race/42.21/media/lua/shared/?.lua;" .. package.path
local Snapshot = require("TGSRR/Run/CharacterSnapshot")
for _, female in ipairs({false, true}) do
    local player = {isFemale = function() return female end}
    local identity = Snapshot.identity(player)
    assert(identity.sex == (female and "female" or "male"))
    assert(Snapshot.observe(player).identity.sex == identity.sex)
end
print("character snapshot tests passed")
