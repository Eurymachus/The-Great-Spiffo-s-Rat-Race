local Icons = {}

local CHURCH = getTexture("media/ui/LootableMaps/map_cross.png")
local MILITARY = getTexture("media/ui/LootableMaps/map_crossedswords.png")

function Icons.get(outpost)
    if outpost and outpost.id == "hog_wallow_military_base" then return MILITARY end
    return CHURCH
end

function Icons.getColor(status, complete)
    if status == "undiscovered" then return 0.58, 0.58, 0.58 end
    return 1, 1, 1
end

return Icons
