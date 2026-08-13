-- Adapted for TGSRR from Twist's TTF sound-debug inspector.
require "ISUI/ISPanel"
require "ISUI/ISTickBox"

TGSRR_SoundDebug = TGSRR_SoundDebug or {}
local TGSRR_ChallengeContext = require "TGSRR/Challenge/Context"

local ENABLE_SOUND_DEBUG_UI = true

local function TGSRR_SoundDebug_IsDebugAllowed()
    return ENABLE_SOUND_DEBUG_UI
        and isDebugEnabled
        and isDebugEnabled()
end

local function TGSRR_SoundDebug_RemoveUI()
    if TGSRR_SoundDebug.ui then
        TGSRR_SoundDebug.ui:removeFromUIManager()
        TGSRR_SoundDebug.ui = nil
    end

    TGSRR_SoundDebug.pending = {}
    TGSRR_SoundDebug.recentAmbient = {}
    TGSRR_SoundDebug.displayedSounds = {}
    TGSRR_SoundDebug.lastVehicle = nil
    TGSRR_SoundDebug.lastVehicleTime = 0
end

if TGSRR_SoundDebug.onWorldSound then Events.OnWorldSound.Remove(TGSRR_SoundDebug.onWorldSound) end
if TGSRR_SoundDebug.onTick then Events.OnTick.Remove(TGSRR_SoundDebug.onTick) end
if TGSRR_SoundDebug.onCreatePlayer then Events.OnCreatePlayer.Remove(TGSRR_SoundDebug.onCreatePlayer) end
if TGSRR_SoundDebug.onMainMenuEnter then Events.OnMainMenuEnter.Remove(TGSRR_SoundDebug.onMainMenuEnter) end
if TGSRR_SoundDebug.onAmbientSound and Events.OnAmbientSound then
    Events.OnAmbientSound.Remove(TGSRR_SoundDebug.onAmbientSound)
end

if not TGSRR_SoundDebug_IsDebugAllowed() then
    TGSRR_SoundDebug_RemoveUI()
    print("[TGSRR Sound Debug] Debug mode is required. Sound debug UI was not started.")
    return
end

TGSRR_SoundDebug.pending = {}
TGSRR_SoundDebug.recentAmbient = {}
TGSRR_SoundDebug.displayedSounds = {}
TGSRRSoundDebugUI = ISPanel:derive("TGSRRSoundDebugUI")

local FONT_TITLE = UIFont.CodeMedium
local FONT_BODY = UIFont.Code
local FONT_VALUE = UIFont.CodeLarge
local FONT_SMALL = UIFont.CodeSmall

local TEXT_MANAGER = getTextManager()

local FONT_HGT_TITLE = TEXT_MANAGER:getFontHeight(FONT_TITLE)
local FONT_HGT_BODY = TEXT_MANAGER:getFontHeight(FONT_BODY)
local FONT_HGT_VALUE = TEXT_MANAGER:getFontHeight(FONT_VALUE)
local FONT_HGT_SMALL = TEXT_MANAGER:getFontHeight(FONT_SMALL)

local UI_PADDING = 14
local HEADER_HEIGHT = FONT_HGT_TITLE + 12
local FILTER_BAR_HEIGHT = 30
local META_ROW_HEIGHT = FONT_HGT_BODY + 8

local MAX_DISPLAYED_SOUNDS = 3
local MAX_SOUND_HISTORY = 24
local SOUND_CARD_GAP = 8

local CARD_HEADER_HEIGHT =
    math.max(
        FONT_HGT_BODY,
        FONT_HGT_SMALL + 8
    )
    + 10

local CARD_VALUE_HEIGHT =
    FONT_HGT_SMALL
    + FONT_HGT_VALUE
    + 18

local SOUND_CARD_HEIGHT =
    CARD_HEADER_HEIGHT
    + CARD_VALUE_HEIGHT
    + META_ROW_HEIGHT * 4
    + 10

local REQUIRED_ROW_WIDTH =
    TEXT_MANAGER:MeasureStringX(
        FONT_BODY,
        "LORE / WEATHER RANGE"
    )
    + TEXT_MANAGER:MeasureStringX(
        FONT_BODY,
        "000-000 TILES"
    )
    + UI_PADDING * 3

local UI_WIDTH = math.max(
    440,
    REQUIRED_ROW_WIDTH
)

local UI_HEIGHT =
    HEADER_HEIGHT
    + FILTER_BAR_HEIGHT
    + UI_PADDING
    + SOUND_CARD_HEIGHT * MAX_DISPLAYED_SOUNDS
    + SOUND_CARD_GAP * (MAX_DISPLAYED_SOUNDS - 1)
    + UI_PADDING

local VEHICLE_SOURCE_DISTANCE = 12.0
local VEHICLE_MEMORY_MS = 5000
local SOUND_BATCH_MS = 180
local RESOLVE_TIMEOUT_MS = 250
local DISPLAY_TIMEOUT_MS = 4000

local function safeCall(object, methodName, ...)
    if not object or not methodName then
        return nil
    end

    local args = { ... }

    local ok, result = pcall(function()
        local method = object[methodName]

        if not method then
            return nil
        end

        return method(object, unpack(args))
    end)

    if not ok then
        return nil
    end

    return result
end

local function safeField(object, fieldName)
    if not object then return nil end

    local ok, result = pcall(function()
        return object[fieldName]
    end)

    if ok then
        return result
    end

    return nil
end

local function round(value)
    return math.floor((value or 0) + 0.5)
end

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

local function distanceSquared(x1, y1, x2, y2)
    local dx = (x1 or 0) - (x2 or 0)
    local dy = (y1 or 0) - (y2 or 0)

    return dx * dx + dy * dy
end

local AMBIENT_SOUND_INFO = {
    MetaAssaultRifle1 = {
        kind = "world",
        label = "Distant assault-rifle fire",
    },
    MetaPistol1 = {
        kind = "world",
        label = "Distant pistol fire",
    },
    MetaPistol2 = {
        kind = "world",
        label = "Distant pistol fire",
    },
    MetaPistol3 = {
        kind = "world",
        label = "Distant pistol fire",
    },
    MetaShotgun1 = {
        kind = "world",
        label = "Distant shotgun fire",
    },
    MetaScream = {
        kind = "world",
        label = "Distant scream",
    },
    MetaDogBark = {
        kind = "animal",
        label = "Distant dog bark",
    },
    MetaOwl = {
        kind = "animal",
        label = "Distant owl",
    },
    MetaWolfHowl = {
        kind = "animal",
        label = "Distant wolf howl",
    },
    burglar2 = {
        kind = "world",
        label = "House alarm",
    },
}

local function isInstanceOf(object, className)
    if not object or not instanceof then
        return false
    end

    local ok, result = pcall(
        instanceof,
        object,
        className
    )

    return ok and result == true
end

local WORLD_CLASS_LABELS = {
    Alarm = "House alarm",
    IsoTelevision = "Television",
    IsoRadio = "Radio",
    IsoGenerator = "Generator",
    IsoJukebox = "Jukebox",
    IsoStove = "Stove",
    IsoClothingWasher = "Washing machine",
    IsoClothingDryer = "Clothing dryer",
    IsoCombinationWasherDryer = "Washer / dryer",
    IsoWaveSignal = "Radio device",
    IsoTrap = "Trap",
}

local function getJavaClassName(object)
    if not object then
        return nil
    end

    local objectText = tostring(object)

    return objectText:match(
        "^([%w_%.%$]+)@"
    )
end

local function getSimpleJavaClassName(object)
    local className = getJavaClassName(object)

    if not className then
        return nil
    end

    return className:match(
        "([%w_%$]+)$"
    )
end

local function makeSoundSourceKey(
    source,
    kind,
    label,
    x,
    y,
    z
)
    if source then
        return tostring(source)
            .. ":"
            .. tostring(kind or "unknown")
            .. ":"
            .. tostring(label or "unknown")
    end

    return tostring(kind or "unknown")
        .. ":"
        .. tostring(label or "unknown")
        .. ":"
        .. tostring(round(x or 0))
        .. ":"
        .. tostring(round(y or 0))
        .. ":"
        .. tostring(round(z or 0))
end

local function fitDebugText(font, text, maximumWidth)
    text = tostring(text or "")

    if TEXT_MANAGER:MeasureStringX(
        font,
        text
    ) <= maximumWidth then
        return text
    end

    local suffix = "..."

    while #text > 0 do
        text = string.sub(
            text,
            1,
            #text - 1
        )

        if TEXT_MANAGER:MeasureStringX(
            font,
            text .. suffix
        ) <= maximumWidth then
            return text .. suffix
        end
    end

    return suffix
end

local function getCategoryPresentation(kind)
    if kind == "vehicle" then
        return "VEHICLE", {
            r = 0.72,
            g = 0.58,
            b = 0.96,
        }
    end

    if kind == "animal" then
        return "ANIMAL", {
            r = 0.38,
            g = 0.86,
            b = 0.42,
        }
    end

    if kind == "world" then
        return "WORLD", {
            r = 0.96,
            g = 0.64,
            b = 0.20,
        }
    end

    return "PLAYER", {
        r = 0.20,
        g = 0.72,
        b = 0.92,
    }
end

local function getSoundCategory(sound)
    if sound and sound.vehicle then
        return "vehicle"
    end

    return sound and sound.kind or "world"
end

local function getRangeColor(radius)
    if radius and radius > 40 then
        return {
            r = 0.96,
            g = 0.32,
            b = 0.26,
        }
    end

    if radius and radius > 15 then
        return {
            r = 0.98,
            g = 0.68,
            b = 0.22,
        }
    end

    return {
        r = 0.32,
        g = 0.82,
        b = 0.52,
    }
end

local function findVehicleNearSound(x, y, z, maxDistance)
    local cell = getCell and getCell() or nil
    local vehicles = safeCall(cell, "getVehicles")
    local vehicleCount = safeCall(vehicles, "size") or 0
    local maximumDistanceSquared = maxDistance * maxDistance

    for i = 0, vehicleCount - 1 do
        local vehicle = safeCall(vehicles, "get", i)

        if vehicle then
            local vehicleX = safeCall(vehicle, "getX")
            local vehicleY = safeCall(vehicle, "getY")
            local vehicleZ = safeCall(vehicle, "getZ")

            if vehicleX and vehicleY and vehicleZ then
                local sameFloor =
                    round(vehicleZ) == round(z or 0)

                local nearSound =
                    distanceSquared(
                        vehicleX,
                        vehicleY,
                        x,
                        y
                    ) <= maximumDistanceSquared

                if sameFloor and nearSound then
                    return vehicle
                end
            end
        end
    end

    return nil
end

local function findRecentAmbientSound(x, y, soundTime)
    local recent = TGSRR_SoundDebug.recentAmbient

    for i = #recent, 1, -1 do
        local ambient = recent[i]
        local timeDifference = math.abs(
            (ambient.time or 0) - (soundTime or 0)
        )

        if timeDifference <= 2500 then
            local nearSound =
                distanceSquared(
                    ambient.x,
                    ambient.y,
                    x,
                    y
                ) <= 24 * 24

            if nearSound then
                local info = AMBIENT_SOUND_INFO[ambient.name]

                if info then
                    return info.kind, info.label
                end

                if ambient.name and ambient.name ~= "" then
                    return "world", "Ambient: " .. ambient.name
                end
            end
        end
    end

    return nil, nil
end

local function getTrackedPlayer()
    local player = getSpecificPlayer and getSpecificPlayer(0) or nil

    if not player and getPlayer then
        player = getPlayer()
    end

    return player
end

local function getVehicleForPlayer(player)
    if not player then return nil end

    local vehicle = safeCall(player, "getVehicle")

    if vehicle then
        TGSRR_SoundDebug.lastVehicle = vehicle
        TGSRR_SoundDebug.lastVehicleTime = getTimestampMs()
        return vehicle
    end

    if TGSRR_SoundDebug.lastVehicle
    and getTimestampMs() - (TGSRR_SoundDebug.lastVehicleTime or 0) <= VEHICLE_MEMORY_MS then
        return TGSRR_SoundDebug.lastVehicle
    end

    return nil
end

local function classifySource(player, source, x, y, z)
    local simpleClass = getSimpleJavaClassName(source)

    if simpleClass == "IsoPlayer"
    or isInstanceOf(source, "IsoPlayer") then
        return "player"
    end

    if simpleClass == "IsoAnimal"
    or isInstanceOf(source, "IsoAnimal") then
        return "animal"
    end

    return "world"
end

local function getItemShoutType(item)
    if not item then return nil end

    return safeCall(item, "getShoutType")
end

local function getShoutItem(player)
    if not player then return nil end

    local primary = safeCall(player, "getPrimaryHandItem")
    if getItemShoutType(primary) then
        return primary
    end

    local secondary = safeCall(player, "getSecondaryHandItem")
    if getItemShoutType(secondary) then
        return secondary
    end

    local wornItems = safeCall(player, "getWornItems")
    local size = safeCall(wornItems, "size") or 0

    for i = 0, size - 1 do
        local item = safeCall(wornItems, "getItemByIndex", i)

        if getItemShoutType(item) then
            return item
        end
    end

    return nil
end

local function hasItemTag(item, tag)
    if not item or not tag then return false end

    return safeCall(item, "hasTag", tag) == true
end

local function getPlayerSoundLabel(player, radius, volume)
    if not player then
        return "Player sound"
    end

    local callOut = safeField(player, "callOut") == true
    local primary = safeCall(player, "getPrimaryHandItem")
    local secondary = safeCall(player, "getSecondaryHandItem")

    local megaphoneTag = ItemTag and ItemTag.MEGAPHONE or nil

    local hasMegaphone =
        hasItemTag(primary, megaphoneTag)
        or hasItemTag(secondary, megaphoneTag)

    local shoutItem = getShoutItem(player)

    if callOut then
        if shoutItem then
            return safeCall(shoutItem, "getDisplayName") or "Shout item"
        end

        if hasMegaphone then
            if safeCall(player, "isSneaking") then
                return "Megaphone whisper"
            end

            return "Megaphone shout"
        end

        if safeCall(player, "isSneaking") then
            return "Whisper"
        end

        return "Shout"
    end

    if radius == 6 then
        return "Whisper"
    end

    if radius == 18 then
        return "Megaphone whisper"
    end

    if radius == 90 then
        return "Megaphone shout"
    end

    if safeCall(player, "isPlayerMoving")
    and radius == volume
    and radius <= 40 then
        if safeCall(player, "isSprinting") then
            return "Sprint footsteps"
        end

        if safeCall(player, "isRunning") then
            return "Run footsteps"
        end

        if safeCall(player, "isSneaking") then
            return "Sneak footsteps"
        end

        return "Footsteps"
    end

    if radius == 35 and volume == 40 then
        return "Cough"
    end

    return "Player sound"
end

local function getServerVehicleAttractionMultiplier()
    local multiplayer =
        (isClient and isClient())
        or (isServer and isServer())

    if not multiplayer or not getServerOptions then
        return 1.0
    end

    local options = getServerOptions()

    local value = tonumber(
        safeCall(
            options,
            "getDouble",
            "CarEngineAttractionModifier"
        )
    )

    if value == nil then
        return 1.0
    end

    return math.max(0.0, value)
end

local function getVehicleEngineData(vehicle)
    if not vehicle then
        return nil
    end

    local vehicleLoudness = tonumber(
        safeCall(
            vehicle,
            "getEngineLoudness"
        )
    )

    if vehicleLoudness == nil then
        return nil
    end

    local script = safeCall(
        vehicle,
        "getScript"
    )

    local scriptLoudness = tonumber(
        safeCall(
            script,
            "getEngineLoudness"
        )
    ) or 0

    local engineSpeed = math.max(
        0,
        tonumber(
            safeCall(
                vehicle,
                "getEngineSpeed"
            )
        ) or 0
    )

    local sandboxMultiplier =
        SandboxVars
        and tonumber(
            SandboxVars.ZombieAttractionMultiplier
        )
        or 1.0

    local serverMultiplier =
        getServerVehicleAttractionMultiplier()

    -- getEngineLoudness() already includes the sandbox
    -- multiplier and the muffler condition.
    local currentLoudness = math.floor(
        vehicleLoudness
        * engineSpeed
        / 2500.0
    )

    local cappedRPM = math.min(
        engineSpeed,
        2000.0
    )

    -- VehicleEngine.updateWorldSounds() casts this multiplier to
    -- an integer before applying it. Build 42.20 caps RPM at 2000,
    -- so the resulting multiplier is currently always 1.
    currentLoudness = math.floor(
        currentLoudness
        * math.floor(
            1.0
            + cappedRPM / 4000.0
        )
    )

    -- Vanilla applies this additional modifier only
    -- when the WorldSound is generated by a server.
    currentLoudness = math.floor(
        currentLoudness
        * serverMultiplier
    )

    return {
        scriptLoudness = scriptLoudness,
        vehicleLoudness = vehicleLoudness,
        engineSpeed = engineSpeed,

        sandboxMultiplier = sandboxMultiplier,
        serverMultiplier = serverMultiplier,

        effectiveLoudness = currentLoudness,

        fullRadius = math.max(
            8,
            currentLoudness
        ),

        halfRadius = math.max(
            8,
            math.floor(currentLoudness / 2)
        ),

        quarterRadius = math.max(
            8,
            math.floor(currentLoudness / 4)
        ),

        normalRadius = math.max(
            8,
            math.floor(currentLoudness / 6)
        ),

        animalRadius = math.max(
            26,
            math.floor(currentLoudness / 6)
        ),

        expectedVolume = math.max(
            6,
            math.floor(currentLoudness / 3)
        ),
    }
end

local function getVehicleEnginePulseName(
    data,
    radius,
    stressZombies,
    stressAnimals
)
    if not data then
        return "ENGINE PULSE"
    end

    if stressAnimals and not stressZombies then
        return "ANIMAL PULSE"
    end

    local matches = {}

    if radius == data.fullRadius then
        matches[#matches + 1] = "FULL BURST"
    end

    if radius == data.halfRadius then
        matches[#matches + 1] = "HALF BURST"
    end

    if radius == data.quarterRadius then
        matches[#matches + 1] = "QUARTER BURST"
    end

    if radius == data.normalRadius then
        matches[#matches + 1] = "NORMAL PULSE"
    end

    if #matches == 1 then
        return matches[1]
    end

    -- Low engine-loudness values can cause several
    -- formulas to result in the minimum radius of 8.
    return "ENGINE PULSE"
end

local function getVehicleSoundInfo(
    vehicle,
    radius,
    volume,
    repeating,
    stressZombies,
    stressAnimals
)
    if radius == 150
    and volume == 150
    and not repeating then
        return "Vehicle horn / alarm", nil, nil
    end

    if radius == 100
    and volume == 60
    and repeating then
        return "Vehicle siren", nil, nil
    end

    if radius == 20
    and volume == 20
    and not repeating then
        return "Vehicle impact", nil, nil
    end

    if repeating then
        local engineData =
            getVehicleEngineData(vehicle)

        local pulseName =
            getVehicleEnginePulseName(
                engineData,
                radius,
                stressZombies,
                stressAnimals
            )

        return "Vehicle engine",
            pulseName,
            engineData
    end

    return "Vehicle sound", nil, nil
end

local function getAnimalSoundLabel(source)
    if not source then
        return "Animal sound"
    end

    local name = safeCall(source, "getFullName")

    if not name or name == "" then
        name = safeCall(source, "getAnimalType")
    end

    if name and name ~= "" then
        return tostring(name) .. " vocalization"
    end

    return "Animal vocalization"
end

local function getWorldSoundInfo(
    source,
    x,
    y,
    z,
    radius,
    volume,
    repeating,
    stressZombies,
    stressAnimals,
    sourceIsZombie,
    sourceIsPlayerBase,
    soundTime
)
    local simpleClass =
        getSimpleJavaClassName(source)

    if simpleClass == "Alarm" then
        return "world",
            "House alarm",
            nil,
            nil,
            nil
    end

    local ambientKind, ambientLabel =
        findRecentAmbientSound(
            x,
            y,
            soundTime
        )

    if ambientLabel then
        return ambientKind,
            ambientLabel,
            nil,
            nil,
            nil
    end

    if not source
    and radius == 500
    and volume == 500 then
        return "world",
            "Helicopter",
            nil,
            nil,
            nil
    end

    if not source
    and radius == 5000
    and volume == 5000 then
        return "world",
            "Thunder",
            nil,
            nil,
            nil
    end

    if not source and volume == 3 then
        return "world",
            "Alarm clock",
            nil,
            nil,
            nil
    end

    local vehicle = nil

    if simpleClass == "BaseVehicle"
    or isInstanceOf(
        source,
        "BaseVehicle"
    ) then
        vehicle = source
    elseif not source then
        local possibleVehicleSound =
            radius == 150
                and volume == 150
            or radius == 100
                and volume == 60
            or radius == 20
                and volume == 20
            or repeating
                and volume >= 6
                and radius >= 8

        if possibleVehicleSound then
            vehicle = findVehicleNearSound(
                x,
                y,
                z,
                VEHICLE_SOURCE_DISTANCE
            )
        end
    end

    if vehicle then
        local label
        local enginePulse
        local engineData

        label, enginePulse, engineData =
            getVehicleSoundInfo(
                vehicle,
                radius,
                volume,
                repeating,
                stressZombies,
                stressAnimals
            )

        return "world",
            label,
            vehicle,
            enginePulse,
            engineData
    end

    if sourceIsZombie
    or simpleClass == "IsoZombie"
    or isInstanceOf(
        source,
        "IsoZombie"
    ) then
        return "world",
            "Zombie sound",
            nil,
            nil,
            nil
    end

    local knownLabel =
        simpleClass
        and WORLD_CLASS_LABELS[simpleClass]
        or nil

    if knownLabel then
        return "world",
            knownLabel,
            nil,
            nil,
            nil
    end

    if sourceIsPlayerBase then
        return "world",
            "Powered appliance",
            nil,
            nil,
            nil
    end

    if not source
    and radius == 600
    and volume == 600 then
        return "world",
            "Meta event / house alarm",
            nil,
            nil,
            nil
    end

    if source then
        if simpleClass and simpleClass ~= "" then
            return "world",
                simpleClass .. " sound",
                nil,
                nil,
                nil
        end

        return "world",
            "World object sound",
            nil,
            nil,
            nil
    end

    return "world",
        "Source-less world sound",
        nil,
        nil,
        nil
end

local function getWeatherHearingMultiplier()
    local climate = getClimateManager and getClimateManager() or nil

    if not climate then
        return 1.0
    end

    local rain = safeCall(climate, "getRainIntensity") or 0
    local fog = safeCall(climate, "getFogIntensity") or 0

    return math.max(
        0,
        1.0 - rain * 0.33 - fog * 0.10
    )
end

local function getZombieRangeText(radius)
    if not radius then
        return "None"
    end

    local hearing = 2

    if SandboxVars
    and SandboxVars.ZombieLore
    and SandboxVars.ZombieLore.Hearing then
        hearing = SandboxVars.ZombieLore.Hearing
    end

    local weatherMultiplier = getWeatherHearingMultiplier()

    local minimumMultiplier = 1.0
    local maximumMultiplier = 1.0

    if hearing == 1 then
        minimumMultiplier = 3.0
        maximumMultiplier = 3.0
    elseif hearing == 3 then
        minimumMultiplier = 0.45
        maximumMultiplier = 0.45
    elseif hearing == 4 then
        minimumMultiplier = 0.45
        maximumMultiplier = 3.0
    elseif hearing == 5 then
        minimumMultiplier = 0.45
        maximumMultiplier = 1.0
    end

    local minimum = math.max(
        1,
        round(radius * minimumMultiplier * weatherMultiplier)
    )

    local maximum = math.max(
        1,
        round(radius * maximumMultiplier * weatherMultiplier)
    )

    if minimum == maximum then
        return tostring(maximum) .. " tiles"
    end

    return tostring(minimum) .. "-" .. tostring(maximum) .. " tiles"
end

local function sourceMatches(candidate, soundSource)
    if candidate.source == soundSource then
        return true
    end

    return candidate.source == nil and soundSource == nil
end

local function soundMatchesCandidate(candidate, sound)
    if not sound then return false end

    return safeField(sound, "x") == candidate.x
        and safeField(sound, "y") == candidate.y
        and safeField(sound, "z") == candidate.z
        and safeField(sound, "radius") == candidate.radius
        and safeField(sound, "volume") == candidate.volume
        and sourceMatches(
            candidate,
            safeField(sound, "source")
        )
end

local function makeResolvedRecord(candidate, sound)
    local source = candidate.source

    if sound then
        source =
            safeField(sound, "source")
            or source
    end

    local stressZombies =
        sound
        and safeField(
            sound,
            "stressZombies"
        )

    local stressAnimals =
        sound
        and safeField(
            sound,
            "stressAnimals"
        )

    local stressHumans =
        sound
        and safeField(
            sound,
            "stresshumans"
        )

    local repeating =
        sound
        and safeField(
            sound,
            "repeating"
        )

    local sourceIsZombie =
        sound
        and safeField(
            sound,
            "sourceIsZombie"
        )

    local sourceIsPlayerBase =
        sound
        and safeField(
            sound,
            "sourceIsPlayerBase"
        )

    if stressZombies == nil then
        stressZombies = true
    end

    if stressAnimals == nil then
        stressAnimals = false
    end

    if stressHumans == nil then
        stressHumans = false
    end

    if repeating == nil then
        repeating = false
    end

    if sourceIsZombie == nil then
        sourceIsZombie = false
    end

    if sourceIsPlayerBase == nil then
        sourceIsPlayerBase = false
    end

    local kind = candidate.kind
    local label
    local vehicle = nil
    local enginePulse = nil
    local engineData = nil

    if kind == "player" then
        label = getPlayerSoundLabel(
            source or getTrackedPlayer(),
            candidate.radius,
            candidate.volume
        )
    elseif kind == "animal" then
        label = getAnimalSoundLabel(source)
    else
        kind,
        label,
        vehicle,
        enginePulse,
        engineData =
            getWorldSoundInfo(
                source,
                candidate.x,
                candidate.y,
                candidate.z,
                candidate.radius,
                candidate.volume,
                repeating,
                stressZombies,
                stressAnimals,
                sourceIsZombie,
                sourceIsPlayerBase,
                candidate.time
            )
    end

    local keySource =
        vehicle or source

    return {
        kind = kind,
        label = label,

        sourceKey = makeSoundSourceKey(
            keySource,
            kind,
            label,
            candidate.x,
            candidate.y,
            candidate.z
        ),

        x = candidate.x,
        y = candidate.y,
        z = candidate.z,

        radius = candidate.radius,
        volume = candidate.volume,

        stressZombies = stressZombies,
        stressAnimals = stressAnimals,
        stressHumans = stressHumans,

        repeating = repeating,

        vehicle = vehicle,
        enginePulse = enginePulse,
        engineData = engineData,

        time = candidate.time,
    }
end

local function updateDisplayedSound(record)
    local sounds =
        TGSRR_SoundDebug.displayedSounds

    local current = nil

    for i = #sounds, 1, -1 do
        if sounds[i].sourceKey
        == record.sourceKey then
            current = table.remove(
                sounds,
                i
            )

            break
        end
    end

    local sameBatch =
        current
        and current.kind == record.kind
        and current.label == record.label
        and record.time
            - (current.batchTime or 0)
            <= SOUND_BATCH_MS

    if not sameBatch then
        local peakZombieRadius =
            current
            and current.zombieRadius
            or nil

        local peakAnimalRadius =
            current
            and current.animalRadius
            or nil

        local peakEnginePulse =
            current
            and current.enginePulse
            or nil

        current = {
            kind = record.kind,
            label = record.label,
            sourceKey = record.sourceKey,

            x = record.x,
            y = record.y,
            z = record.z,

            zombieRadius = peakZombieRadius,
            animalRadius = peakAnimalRadius,

            volume = record.volume,
            repeating = record.repeating,

            vehicle = record.vehicle,
            enginePulse = peakEnginePulse,
            engineData = record.engineData,

            lastTime = record.time,
            batchTime = record.time,
        }
    else
        current.x = record.x
        current.y = record.y
        current.z = record.z

        current.lastTime = record.time

        current.repeating =
            current.repeating
            or record.repeating

        current.volume = math.max(
            current.volume or 0,
            record.volume or 0
        )

        current.vehicle =
            record.vehicle
            or current.vehicle

        current.engineData =
            record.engineData
            or current.engineData
    end

    if record.stressZombies then
        local previousRadius =
            current.zombieRadius or -1

        if record.radius >= previousRadius then
            current.enginePulse =
                record.enginePulse
                or current.enginePulse
        end

        current.zombieRadius = math.max(
            current.zombieRadius or 0,
            record.radius or 0
        )
    end

    if record.stressAnimals then
        current.animalRadius = math.max(
            current.animalRadius or 0,
            record.radius or 0
        )
    end

    table.insert(
        sounds,
        1,
        current
    )

    while #sounds > MAX_SOUND_HISTORY do
        table.remove(sounds)
    end

    if TGSRR_SoundDebug.ui then
        TGSRR_SoundDebug.ui.soundList =
            sounds
    end
end

local function resolvePendingSounds()
    if #TGSRR_SoundDebug.pending == 0 then
        return
    end

    local now = getTimestampMs()

    local manager =
        getWorldSoundManager
        and getWorldSoundManager()
        or nil

    local soundList = safeField(manager, "soundList")
    local soundCount = safeCall(soundList, "size") or 0

    local claimedIndices = {}
    local resolvedNewestFirst = {}
    local keep = {}

    for pendingIndex = #TGSRR_SoundDebug.pending, 1, -1 do
        local candidate = TGSRR_SoundDebug.pending[pendingIndex]
        local matchedSound = nil

        for soundIndex = soundCount - 1, 0, -1 do
            if not claimedIndices[soundIndex] then
                local sound = safeCall(
                    soundList,
                    "get",
                    soundIndex
                )

                if soundMatchesCandidate(candidate, sound) then
                    matchedSound = sound
                    claimedIndices[soundIndex] = true
                    break
                end
            end
        end

        if matchedSound then
            table.insert(
                resolvedNewestFirst,
                makeResolvedRecord(candidate, matchedSound)
            )
        elseif now - candidate.time >= RESOLVE_TIMEOUT_MS then
            table.insert(
                resolvedNewestFirst,
                makeResolvedRecord(candidate, nil)
            )
        else
            table.insert(keep, 1, candidate)
        end
    end

    TGSRR_SoundDebug.pending = keep

    for i = #resolvedNewestFirst, 1, -1 do
        updateDisplayedSound(resolvedNewestFirst[i])
    end
end

function TGSRRSoundDebugUI:savePosition()
    local data = ModData.getOrCreate("TGSRRSoundDebugUI")

    data.x = self:getX()
    data.y = self:getY()
end

function TGSRRSoundDebugUI:onFilterChanged(index, selected, filterKey)
    self.filters[filterKey] = selected == true

    local data = ModData.getOrCreate("TGSRRSoundDebugUI")
    data["filter_" .. filterKey] = self.filters[filterKey]
end

function TGSRRSoundDebugUI:createChildren()
    ISPanel.createChildren(self)

    local saved = ModData.getOrCreate("TGSRRSoundDebugUI")
    local definitions = {
        { key = "player", label = "Player", width = 92 },
        { key = "world", label = "World", width = 88 },
        { key = "animal", label = "Animal", width = 96 },
        { key = "vehicle", label = "Vehicle", width = 104 },
    }

    self.filters = {}
    local x = UI_PADDING
    local y = HEADER_HEIGHT + 5

    for _, definition in ipairs(definitions) do
        local savedValue = saved["filter_" .. definition.key]
        local selected = savedValue == nil or savedValue == true
        self.filters[definition.key] = selected

        local tickBox = ISTickBox:new(
            x,
            y,
            definition.width,
            18,
            "",
            self,
            self.onFilterChanged,
            definition.key
        )
        tickBox:initialise()
        tickBox:addOption(definition.label)
        tickBox:setSelected(1, selected)
        self:addChild(tickBox)

        x = x + definition.width
    end
end

function TGSRRSoundDebugUI:getFilteredSounds()
    local filtered = {}
    local filters = self.filters or {}

    for _, sound in ipairs(self.soundList or {}) do
        local category = getSoundCategory(sound)

        if filters[category] ~= false then
            filtered[#filtered + 1] = sound

            if #filtered >= MAX_DISPLAYED_SOUNDS then
                break
            end
        end
    end

    return filtered
end

function TGSRRSoundDebugUI:onMouseUp(x, y)
    ISPanel.onMouseUp(self, x, y)
    self:savePosition()
end

function TGSRRSoundDebugUI:onMouseUpOutside(x, y)
    ISPanel.onMouseUpOutside(self, x, y)
    self:savePosition()
end

function TGSRRSoundDebugUI:prerender()
    ISPanel.prerender(self)

    local contentX = UI_PADDING
    local contentRight =
        self.width - UI_PADDING

    self:drawRect(
        0,
        0,
        self.width,
        HEADER_HEIGHT,
        0.98,
        0.055,
        0.065,
        0.075
    )

    self:drawRect(
        0,
        0,
        4,
        self.height,
        1.0,
        0.18,
        0.68,
        0.86
    )

    self:drawRect(
        4,
        HEADER_HEIGHT - 1,
        self.width - 4,
        1,
        0.65,
        0.30,
        0.42,
        0.48
    )

    self:drawRect(
        4,
        HEADER_HEIGHT + FILTER_BAR_HEIGHT - 1,
        self.width - 4,
        1,
        0.45,
        0.24,
        0.32,
        0.36
    )

    local titleY = math.floor(
        (
            HEADER_HEIGHT
            - FONT_HGT_TITLE
        ) / 2
    )

    self:drawText(
        "WORLD SOUND MONITOR",
        contentX,
        titleY,
        0.72,
        0.90,
        1.00,
        1.0,
        FONT_TITLE
    )

    self:drawTextRight(
        "[ DRAG ]",
        contentRight,
        titleY,
        0.42,
        0.48,
        0.52,
        1.0,
        FONT_SMALL
    )

    local sounds = self:getFilteredSounds()
    local y = HEADER_HEIGHT + FILTER_BAR_HEIGHT + UI_PADDING

    if #sounds == 0 then
        self:drawText(
            "NO MATCHING SOUND CAPTURED",
            contentX,
            y + 6,
            0.72,
            0.78,
            0.82,
            1.0,
            FONT_BODY
        )

        y = y + FONT_HGT_BODY + 14

        self:drawText(
            "Waiting for player, animal or world",
            contentX,
            y,
            0.46,
            0.51,
            0.55,
            1.0,
            FONT_SMALL
        )

        y = y + FONT_HGT_SMALL + 5

        self:drawText(
            "sound events...",
            contentX,
            y,
            0.46,
            0.51,
            0.55,
            1.0,
            FONT_SMALL
        )

        return
    end

    local cardWidth =
        self.width - UI_PADDING * 2

    for index = 1, math.min(
        #sounds,
        MAX_DISPLAYED_SOUNDS
    ) do
        local data = sounds[index]
        local radius = data.zombieRadius

        local sourceText, sourceColor =
            getCategoryPresentation(
                getSoundCategory(data)
            )

        local rangeColor =
            getRangeColor(radius)

        self:drawRect(
            contentX,
            y,
            cardWidth,
            SOUND_CARD_HEIGHT,
            0.76,
            0.020,
            0.025,
            0.030
        )

        self:drawRectBorder(
            contentX,
            y,
            cardWidth,
            SOUND_CARD_HEIGHT,
            0.62,
            0.22,
            0.28,
            0.32
        )

        self:drawRect(
            contentX,
            y,
            4,
            SOUND_CARD_HEIGHT,
            0.95,
            sourceColor.r,
            sourceColor.g,
            sourceColor.b
        )

        local badgeX = contentX + 12
        local badgeY = y + 8

        local badgeWidth =
            TEXT_MANAGER:MeasureStringX(
                FONT_SMALL,
                sourceText
            )
            + 16

        self:drawRect(
            badgeX,
            badgeY,
            badgeWidth,
            FONT_HGT_SMALL + 8,
            0.90,
            sourceColor.r * 0.18,
            sourceColor.g * 0.18,
            sourceColor.b * 0.18
        )

        self:drawRectBorder(
            badgeX,
            badgeY,
            badgeWidth,
            FONT_HGT_SMALL + 8,
            0.85,
            sourceColor.r,
            sourceColor.g,
            sourceColor.b
        )

        self:drawText(
            sourceText,
            badgeX + 8,
            badgeY + 4,
            sourceColor.r,
            sourceColor.g,
            sourceColor.b,
            1.0,
            FONT_SMALL
        )

        local eventText =
            data.label or "Unknown sound"

        if data.enginePulse then
            eventText =
                eventText
                .. "  ["
                .. data.enginePulse
                .. "]"
        elseif data.repeating then
            eventText =
                eventText
                .. "  [REPEATING]"
        end

        local eventX =
            badgeX
            + badgeWidth
            + 10

        local eventWidth =
            contentRight
            - eventX
            - 10

        eventText = fitDebugText(
            FONT_BODY,
            eventText,
            eventWidth
        )

        self:drawText(
            eventText,
            eventX,
            badgeY + 3,
            0.80,
            0.84,
            0.87,
            1.0,
            FONT_BODY
        )

        local valueY =
            y + CARD_HEADER_HEIGHT

        self:drawRect(
            contentX + 10,
            valueY,
            cardWidth - 20,
            CARD_VALUE_HEIGHT,
            0.70,
            0.012,
            0.016,
            0.020
        )

        self:drawText(
            "ZOMBIE SOUND RADIUS",
            contentX + 21,
            valueY + 6,
            0.46,
            0.54,
            0.58,
            1.0,
            FONT_SMALL
        )

        local radiusText

        if radius then
            radiusText =
                tostring(radius)
                .. " TILES"
        else
            radiusText =
                "NO ZOMBIE SOUND"
        end

        self:drawText(
            radiusText,
            contentX + 20,
            valueY
                + FONT_HGT_SMALL
                + 7,
            rangeColor.r,
            rangeColor.g,
            rangeColor.b,
            1.0,
            FONT_VALUE
        )

        self:drawTextRight(
            "#" .. tostring(index),
            contentRight - 20,
            valueY + 7,
            0.34,
            0.39,
            0.42,
            1.0,
            FONT_SMALL
        )

        local metaY =
            valueY + CARD_VALUE_HEIGHT

        self:drawText(
            "LORE / WEATHER RANGE",
            contentX + 14,
            metaY + 3,
            0.48,
            0.55,
            0.59,
            1.0,
            FONT_BODY
        )

        self:drawTextRight(
            string.upper(
                getZombieRangeText(radius)
            ),
            contentRight - 14,
            metaY + 3,
            rangeColor.r,
            rangeColor.g,
            rangeColor.b,
            1.0,
            FONT_BODY
        )

        self:drawRect(
            contentX + 12,
            metaY + FONT_HGT_BODY + 6,
            cardWidth - 24,
            1,
            0.28,
            0.18,
            0.21,
            0.23
        )

        metaY = metaY + META_ROW_HEIGHT

        local animalText = "NONE"

        if data.animalRadius then
            animalText =
                tostring(data.animalRadius)
                .. " TILES"
        end

        self:drawText(
            "VOLUME "
                .. tostring(
                    data.volume or 0
                ),
            contentX + 14,
            metaY + 3,
            0.70,
            0.74,
            0.77,
            1.0,
            FONT_BODY
        )

        self:drawTextRight(
            "ANIMALS " .. animalText,
            contentRight - 14,
            metaY + 3,
            0.70,
            0.74,
            0.77,
            1.0,
            FONT_BODY
        )

        self:drawRect(
            contentX + 12,
            metaY + FONT_HGT_BODY + 6,
            cardWidth - 24,
            1,
            0.28,
            0.18,
            0.21,
            0.23
        )

        metaY = metaY + META_ROW_HEIGHT

        local engineData = data.engineData

        if engineData then
            self:drawText(
                "ENGINE / SCRIPT / RPM",
                contentX + 14,
                metaY + 3,
                0.48,
                0.55,
                0.59,
                1.0,
                FONT_BODY
            )

            self:drawTextRight(
                tostring(
                    engineData.vehicleLoudness
                )
                .. " / "
                .. tostring(
                    engineData.scriptLoudness
                )
                .. " / "
                .. tostring(
                    round(engineData.engineSpeed)
                ),
                contentRight - 14,
                metaY + 3,
                0.78,
                0.82,
                0.85,
                1.0,
                FONT_BODY
            )
        else
            self:drawText(
                "POSITION",
                contentX + 14,
                metaY + 3,
                0.48,
                0.55,
                0.59,
                1.0,
                FONT_BODY
            )

            self:drawTextRight(
                tostring(round(data.x or 0))
                .. ", "
                .. tostring(round(data.y or 0))
                .. ", "
                .. tostring(round(data.z or 0)),
                contentRight - 14,
                metaY + 3,
                0.70,
                0.74,
                0.77,
                1.0,
                FONT_BODY
            )
        end

        self:drawRect(
            contentX + 12,
            metaY + FONT_HGT_BODY + 6,
            cardWidth - 24,
            1,
            0.28,
            0.18,
            0.21,
            0.23
        )

        metaY = metaY + META_ROW_HEIGHT

        if engineData then
            self:drawText(
                "EFFECTIVE / MULTIPLIERS",
                contentX + 14,
                metaY + 3,
                0.48,
                0.55,
                0.59,
                1.0,
                FONT_BODY
            )

            self:drawTextRight(
                tostring(
                    engineData.effectiveLoudness
                )
                .. "  |  SB x"
                .. string.format(
                    "%.2f",
                    engineData.sandboxMultiplier
                )
                .. "  |  MP x"
                .. string.format(
                    "%.2f",
                    engineData.serverMultiplier
                ),
                contentRight - 14,
                metaY + 3,
                0.78,
                0.82,
                0.85,
                1.0,
                FONT_BODY
            )
        else
            self:drawText(
                "EVENT MODE",
                contentX + 14,
                metaY + 3,
                0.48,
                0.55,
                0.59,
                1.0,
                FONT_BODY
            )

            self:drawTextRight(
                data.repeating
                    and "REPEATING"
                    or "ONE-SHOT",
                contentRight - 14,
                metaY + 3,
                0.70,
                0.74,
                0.77,
                1.0,
                FONT_BODY
            )
        end
        local fill = clamp(
            (radius or 0) / 150.0,
            0,
            1
        )

        local barX = contentX + 10
        local barY =
            y + SOUND_CARD_HEIGHT - 6

        local barWidth =
            cardWidth - 20

        self:drawRect(
            barX,
            barY,
            barWidth,
            3,
            0.75,
            0.09,
            0.11,
            0.13
        )

        self:drawRect(
            barX,
            barY,
            barWidth * fill,
            3,
            1.0,
            rangeColor.r,
            rangeColor.g,
            rangeColor.b
        )

        y =
            y
            + SOUND_CARD_HEIGHT
            + SOUND_CARD_GAP
    end
end

function TGSRRSoundDebugUI:new(x, y)
    local o = ISPanel.new(
        self,
        x,
        y,
        UI_WIDTH,
        UI_HEIGHT
    )

    o.backgroundColor = {
        r = 0.025,
        g = 0.030,
        b = 0.035,
        a = 0.94,
    }

    o.borderColor = {
        r = 0.22,
        g = 0.30,
        b = 0.34,
        a = 0.95,
    }

    o.moveWithMouse = true

    o.filters = {}
    o.soundList =
        TGSRR_SoundDebug.displayedSounds

    return o
end

function TGSRR_SoundDebug.onAmbientSound(name, x, y)
    if not TGSRR_SoundDebug_IsDebugAllowed() then
        return
    end

    local recent = TGSRR_SoundDebug.recentAmbient
    local now = getTimestampMs()

    table.insert(recent, {
        name = tostring(name or ""),
        x = tonumber(x) or 0,
        y = tonumber(y) or 0,
        time = now,
    })

    while #recent > 32 do
        table.remove(recent, 1)
    end

    for i = #recent, 1, -1 do
        if now - (recent[i].time or 0) > 10000 then
            table.remove(recent, i)
        end
    end
end

function TGSRR_SoundDebug.onWorldSound(
    x,
    y,
    z,
    radius,
    volume,
    source
)
    if not TGSRR_SoundDebug_IsDebugAllowed() then
        return
    end

    local player = getTrackedPlayer()

    if not player then
        return
    end

    local kind = classifySource(
        player,
        source,
        x,
        y,
        z
    )

    if not kind then
        return
    end

    table.insert(TGSRR_SoundDebug.pending, {
        kind = kind,
        source = source,

        x = x,
        y = y,
        z = z,

        radius = radius,
        volume = volume,

        time = getTimestampMs(),
    })
end

function TGSRR_SoundDebug.onTick()
    if not TGSRR_SoundDebug_IsDebugAllowed() then
        TGSRR_SoundDebug_RemoveUI()
        return
    end

    local player = getTrackedPlayer()

    if player then
        getVehicleForPlayer(player)
    end

    resolvePendingSounds()

    local sounds =
        TGSRR_SoundDebug.displayedSounds

    local now = getTimestampMs()

    for i = #sounds, 1, -1 do
        local sound = sounds[i]

        if now
            - (sound.lastTime or 0)
            > DISPLAY_TIMEOUT_MS then
            table.remove(
                sounds,
                i
            )
        end
    end

    if TGSRR_SoundDebug.ui then
        TGSRR_SoundDebug.ui.soundList =
            sounds
    end
end

function TGSRR_SoundDebug.onCreatePlayer(playerNum, player)
    if not TGSRR_ChallengeContext.isActive()
            or not TGSRR_SoundDebug_IsDebugAllowed() then
        TGSRR_SoundDebug_RemoveUI()
        return
    end

    if playerNum ~= 0 then
        return
    end

    if TGSRR_SoundDebug.ui then
        TGSRR_SoundDebug.ui:removeFromUIManager()
        TGSRR_SoundDebug.ui = nil
    end

    local saved = ModData.getOrCreate("TGSRRSoundDebugUI")

    local x = tonumber(saved.x) or 20
    local y = tonumber(saved.y) or 300

    x = clamp(
        x,
        0,
        math.max(
            0,
            getCore():getScreenWidth() - UI_WIDTH
        )
    )

    y = clamp(
        y,
        0,
        math.max(
            0,
            getCore():getScreenHeight() - UI_HEIGHT
        )
    )

    local ui = TGSRRSoundDebugUI:new(x, y)

    ui:initialise()
    ui:addToUIManager()
    ui:setAlwaysOnTop(true)
    ui:setVisible(true)

    TGSRR_SoundDebug.ui = ui
end

function TGSRR_SoundDebug.onMainMenuEnter()
    TGSRR_SoundDebug.recentAmbient = {}

    if TGSRR_SoundDebug.ui then
        TGSRR_SoundDebug.ui:removeFromUIManager()
    end

    TGSRR_SoundDebug.ui = nil
    TGSRR_SoundDebug.pending = {}
    TGSRR_SoundDebug.displayedSounds = {}
    TGSRR_SoundDebug.lastVehicle = nil
    TGSRR_SoundDebug.lastVehicleTime = 0
end

Events.OnWorldSound.Add(TGSRR_SoundDebug.onWorldSound)
Events.OnTick.Add(TGSRR_SoundDebug.onTick)
Events.OnCreatePlayer.Add(TGSRR_SoundDebug.onCreatePlayer)
Events.OnMainMenuEnter.Add(TGSRR_SoundDebug.onMainMenuEnter)

if Events.OnAmbientSound then
    Events.OnAmbientSound.Add(
        TGSRR_SoundDebug.onAmbientSound
    )
end

local existingPlayer = getTrackedPlayer()

if existingPlayer then
    TGSRR_SoundDebug.onCreatePlayer(0, existingPlayer)
end
