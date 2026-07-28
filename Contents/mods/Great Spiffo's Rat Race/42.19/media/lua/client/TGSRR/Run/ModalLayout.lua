local ModalLayout = {}

function ModalLayout.center(width, height, playerNum)
    playerNum = math.max(0, math.floor(tonumber(playerNum) or 0))
    local left = getPlayerScreenLeft
        and tonumber(getPlayerScreenLeft(playerNum)) or 0
    local top = getPlayerScreenTop
        and tonumber(getPlayerScreenTop(playerNum)) or 0
    local screenWidth = getPlayerScreenWidth
        and tonumber(getPlayerScreenWidth(playerNum))
        or tonumber(getCore():getScreenWidth()) or width
    local screenHeight = getPlayerScreenHeight
        and tonumber(getPlayerScreenHeight(playerNum))
        or tonumber(getCore():getScreenHeight()) or height
    return math.floor(left + (screenWidth - width) / 2),
        math.floor(top + (screenHeight - height) / 2)
end

function ModalLayout.fitAndCenter(width, height, text, playerNum)
    if ISModalDialog and ISModalDialog.CalcSize then
        width, height = ISModalDialog.CalcSize(width, height, text)
    end
    local x, y = ModalLayout.center(width, height, playerNum)
    return x, y, width, height
end

return ModalLayout
