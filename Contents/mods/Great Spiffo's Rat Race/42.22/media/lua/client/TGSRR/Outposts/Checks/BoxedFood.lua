local BoxedFood = {}

local CONTENTS_PER_BOX = 6
local CONTENTS_BY_BOX = {
    ["Base.Macandcheese_Box"] = "Base.Macandcheese",
    ["Base.TinnedBeans_Box"] = "Base.TinnedBeans",
    ["Base.CannedBolognese_Box"] = "Base.CannedBolognese",
    ["Base.CannedCarrots_Box"] = "Base.CannedCarrots2",
    ["Base.CannedChili_Box"] = "Base.CannedChili",
    ["Base.CannedCornedBeef_Box"] = "Base.CannedCornedBeef",
    ["Base.CannedCorn_Box"] = "Base.CannedCorn",
    ["Base.CannedFruitCocktail_Box"] = "Base.CannedFruitCocktail",
    ["Base.CannedFruitBeverage_Box"] = "Base.CannedFruitBeverage",
    ["Base.CannedMilk_Box"] = "Base.CannedMilk",
    ["Base.CannedMushroomSoup_Box"] = "Base.CannedMushroomSoup",
    ["Base.CannedPeaches_Box"] = "Base.CannedPeaches",
    ["Base.CannedPeas_Box"] = "Base.CannedPeas",
    ["Base.CannedPineapple_Box"] = "Base.CannedPineapple",
    ["Base.CannedPotato_Box"] = "Base.CannedPotato2",
    ["Base.CannedSardines_Box"] = "Base.CannedSardines",
    ["Base.TinnedSoup_Box"] = "Base.TinnedSoup",
    ["Base.CannedTomato_Box"] = "Base.CannedTomato2",
    ["Base.TunaTin_Box"] = "Base.TunaTin",
    ["Base.Dogfood_Box"] = "Base.Dogfood",
    ["Base.MysteryCan_Box"] = "Base.MysteryCan",
    ["Base.DentedCan_Box"] = "Base.DentedCan",
    ["Base.WaterRationCan_Box"] = "Base.WaterRationCan",
}

function BoxedFood.calories(item, neverSpoils)
    local boxType = item and item.getFullType and item:getFullType() or nil
    local contentsType = CONTENTS_BY_BOX[boxType]
    if not contentsType then return 0 end

    local manager = getScriptManager and getScriptManager() or nil
    local scriptItem = manager and manager:FindItem(contentsType) or nil
    local contents = scriptItem and scriptItem:InstanceItem(nil) or nil
    if not contents or not instanceof(contents, "Food")
            or contents:getOffAgeMax() ~= neverSpoils then
        return 0
    end
    return math.max(0, tonumber(contents:getCalories()) or 0)
        * CONTENTS_PER_BOX
end

return BoxedFood
