require "ISUI/Maps/ISWorldMap"
require "TimedActions/ISReadWorldMap"
require "TimedActions/ISTimedActionQueue"

local Locations = require "TGSRR/Locations/Definitions"
local Outposts = require "TGSRR/Outposts/Definitions"

local WorldMap = {}
local SYMBOL_ID = "Asterisk"
local OUTPOST_SYMBOL_ID = "Cross"
local MILITARY_SYMBOL_ID = "CrossedSwords"
local POSITION_EPSILON = 0.1
local LOCATION_ZOOM = 18

local function locationKey(x, y)
    return tostring(math.floor(x + 0.5)) .. ":"
        .. tostring(math.floor(y + 0.5))
end

local function existingMapSymbols(symbolsAPI)
    local existing = {}
    for index = 0, symbolsAPI:getSymbolCount() - 1 do
        local symbol = symbolsAPI:getSymbolByIndex(index)
        if symbol:isTexture() and not symbol:isUserDefined() then
            local symbolId = symbol:getSymbolID()
            if symbolId == SYMBOL_ID or symbolId == OUTPOST_SYMBOL_ID
                    or symbolId == MILITARY_SYMBOL_ID then
                existing[symbolId .. ":"
                    .. locationKey(symbol:getWorldX(), symbol:getWorldY())] = symbol
            end
        end
    end
    return existing
end

local function ensureSymbol(symbolsAPI, existing, symbolId, anchor, r, g, b)
    if not anchor then return end
    local key = symbolId .. ":" .. locationKey(anchor.x, anchor.y)
    local symbol = existing[key]
    if not symbol then
        symbol = symbolsAPI:addTexture(symbolId, anchor.x, anchor.y)
        symbol:setAnchor(0.5, 0.5)
        symbol:setScale(0.666)
        symbol:setRGBA(r, g, b, 1)
        symbol:setMatchPerspective(true)
        symbol:setApplyZoom(true)
        symbol:setMinZoom(0)
        symbol:setMaxZoom(24)
        symbol:setUserDefined(false)
        existing[key] = symbol
    elseif math.abs(symbol:getWorldX() - anchor.x) > POSITION_EPSILON
            or math.abs(symbol:getWorldY() - anchor.y) > POSITION_EPSILON then
        symbol:setPosition(anchor.x, anchor.y)
    end
end

function WorldMap.ensure(mapUI)
    if not mapUI or not mapUI.mapAPI then return end
    local symbolsAPI = mapUI.mapAPI:getSymbolsAPIv2()
    if not symbolsAPI then return end

    local existing = existingMapSymbols(symbolsAPI)
    for _, location in ipairs(Locations.getAll()) do
        ensureSymbol(symbolsAPI, existing, SYMBOL_ID, location.anchor,
            0.72, 0.12, 0.12)
    end
    for _, outpost in ipairs(Outposts.getAll()) do
        local symbolId = outpost.id == "hog_wallow_military_base"
            and MILITARY_SYMBOL_ID or OUTPOST_SYMBOL_ID
        ensureSymbol(symbolsAPI, existing, symbolId, outpost.anchor,
            0.12, 0.42, 0.72)
    end
end

function WorldMap.showAt(anchor, playerNum)
    if not anchor then return end
    if not ISWorldMap.IsAllowed() then return end

    playerNum = playerNum or 0
    local player = getSpecificPlayer(playerNum)
    if not player then return end

    local tooDarkToRead = player:tooDarkToRead()
    if player:getVehicle() then
        if player:getVehicle():hasLiveBattery() then tooDarkToRead = false end
        if player:getTorchStrength() > 0 then tooDarkToRead = false end
    end
    if getCore():getDebug() then tooDarkToRead = false end
    if ISWorldMap.NeedsLight() and tooDarkToRead and not isAdmin() then
        if not (player:getVehicle()
                and player:getVehicle():getBatteryCharge() > 0) then
            HaloTextHelper.addBadText(player, getText("ContextMenu_TooDark"))
            return
        end
    end

    if ISPostDeathUI and ISPostDeathUI.instance
            and #ISPostDeathUI.instance > 0 then
        return
    end

    player:setJoypadIgnoreAimUntilCentered(true)
    ISTimedActionQueue.clear(player)
    ISTimedActionQueue.add(ISReadWorldMap:new(
        player, anchor.x, anchor.y, LOCATION_ZOOM))
end

if not ISWorldMap.TGSRRLandmarksWrapped then
    local showWorldMap = ISWorldMap.ShowWorldMap
    ISWorldMap.ShowWorldMap = function(playerNum, centerX, centerY, zoom)
        local result = showWorldMap(playerNum, centerX, centerY, zoom)
        WorldMap.ensure(ISWorldMap_instance)
        return result
    end
    ISWorldMap.TGSRRLandmarksWrapped = true
end

return WorldMap
