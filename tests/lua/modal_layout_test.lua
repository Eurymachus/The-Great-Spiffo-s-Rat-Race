local left, top = 100, 50
local screenWidth, screenHeight = 1800, 1000

getPlayerScreenLeft = function(player)
    assert(player == 0)
    return left
end
getPlayerScreenTop = function(player)
    assert(player == 0)
    return top
end
getPlayerScreenWidth = function(player)
    assert(player == 0)
    return screenWidth
end
getPlayerScreenHeight = function(player)
    assert(player == 0)
    return screenHeight
end

local ModalLayout = require "TGSRR/Run/ModalLayout"
local x, y = ModalLayout.center(760, 320, 0)
assert(x == 620)
assert(y == 390)
assert(x + 760 / 2 == left + screenWidth / 2)
assert(y + 320 / 2 == top + screenHeight / 2)

ISModalDialog = {
    CalcSize = function(width, height, text)
        assert(width == 760 and height == 320 and text == "wide text")
        return 980, 360
    end,
}
local fittedX, fittedY, fittedWidth, fittedHeight =
    ModalLayout.fitAndCenter(760, 320, "wide text", 0)
assert(fittedWidth == 980 and fittedHeight == 360)
assert(fittedX + fittedWidth / 2 == left + screenWidth / 2)
assert(fittedY + fittedHeight / 2 == top + screenHeight / 2)

print("modal layout test passed")
