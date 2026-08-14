local Outposts = require "TGSRR/Outposts/Registry"

local NAME_KEYS = {
    brandenburg = "UI_TGSRR_Outpost_Brandenburg",
    echo_creek = "UI_TGSRR_Outpost_EchoCreek",
    ekron = "UI_TGSRR_Outpost_Ekron",
    fallas_lake = "UI_TGSRR_Outpost_FallasLake",
    hog_wallow_military_base = "UI_TGSRR_Outpost_HogWallowMilitaryBase",
    irvington = "UI_TGSRR_Outpost_Irvington",
    louisville = "UI_TGSRR_Outpost_Louisville",
    march_ridge = "UI_TGSRR_Outpost_MarchRidge",
    muldraugh = "UI_TGSRR_Outpost_Muldraugh",
    riverside = "UI_TGSRR_Outpost_Riverside",
    rosewood = "UI_TGSRR_Outpost_Rosewood",
    valley_station = "UI_TGSRR_Outpost_ValleyStation",
    west_point = "UI_TGSRR_Outpost_WestPoint",
}

local function building(id, options)
    local value = options or {}
    value.id = tostring(id)
    value.requireAllRoomsActivated = value.requireAllRoomsActivated ~= false
    value.requireZombieClearance = value.requireZombieClearance ~= false
    return value
end

local function add(id, name, anchor, zone, center, buildings, options)
    options = options or {}
    return Outposts.add({
        id = id,
        name = name,
        nameKey = NAME_KEYS[id],
        anchor = { x = anchor[1], y = anchor[2], z = anchor[3] },
        coreZone = { minX = zone[1], minY = zone[2], maxX = zone[3], maxY = zone[4] },
        clearance = { centerX = center[1], centerY = center[2], width = 150, height = 150 },
        sealingLevel = options.sealingLevel or 0,
        supportRadius = options.supportRadius or 15,
        buildings = buildings,
        requireAllRoomsActivated = true,
        requireZombieClearance = true,
    })
end

add("brandenburg", "Brandenburg", {2093, 6029, 0}, {2068, 6002, 2099, 6045}, {2083, 6023}, {
    building("6473958824083477"),
})

add("echo_creek", "Echo Creek", {3538, 11207, 0}, {3531, 11198, 3555, 11224}, {3541, 11211}, {
    building("12103479833133062", {
        excludeRoomIds = {
            "12103479833133143", -- inaccessible decorative bell tower
        },
    }),
})

add("ekron", "Ekron", {443, 9923, 0}, {438, 9913, 470, 9942}, {450, 9926}, {
    building("10696053409972226", { underground = true }),
    building("10696053409972269", {
        -- Floors 3 through 5 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 1 },
    }),
})

add("fallas_lake", "Fallas Lake", {7222, 8526, 0}, {7217, 8520, 7229, 8539}, {7223, 8529}, {
    building("9288794490535943", {
        -- Floors 2 through 4 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 0 },
    }),
})

add("hog_wallow_military_base", "Hog Wallow Military Base", {5559, 12487, 0}, {5536, 12439, 5583, 12505}, {5560, 12472}, {
    building("13510889076424704", { underground = true }),
    building("13510889076424705"),
})

add("irvington", "Irvington", {2433, 14227, 0}, {2406, 14211, 2440, 14255}, {2423, 14233}, {
    building("15481162373791744", { underground = true }),
    building("15481162373791782", {
        -- Floors 3 through 5 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 1 },
        excludeRoomIds = {
            "15481162373792021", -- inaccessible decorative bell tower
        },
    }),
})

add("louisville", "Louisville", {12608, 3369, 0}, {12599, 3353, 12618, 3384}, {12608, 3368}, {
    building("3659385150636034"),
})

add("march_ridge", "March Ridge", {10330, 12788, 0}, {10317, 12779, 10345, 12816}, {10331, 12797}, {
    building("13792445657513985"),
})

add("muldraugh", "Muldraugh", {10760, 10165, 0}, {10750, 10160, 10773, 10170}, {10761, 10165}, {
    building("10977700185374723", {
        -- Floors 3 and 4 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 1 },
    }),
})

add("riverside", "Riverside", {6549, 5368, 0}, {6542, 5351, 6585, 5387}, {6564, 5369}, {
    building("5629606908395530", {
        -- Floors 3 through 6 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 1 },
    }),
})

add("rosewood", "Rosewood", {8134, 11518, 0}, {8118, 11504, 8155, 11525}, {8136, 11514}, {
    building("12385032119255075", {
        -- Floors 4 through 7 are inaccessible decorative church-spire rooms.
        activationLevels = { min = 0, max = 2 },
    }),
})

add("valley_station", "Valley Station", {12849, 4953, 0}, {12843, 4949, 12869, 4965}, {12848, 4957}, {
    building("5348239305867264"),
    building("5348239305867265"),
})

add("west_point", "West Point", {11970, 7000, 0}, {11959, 6975, 11985, 7007}, {11971, 6992}, {
    building("7600021939683331"),
})

return Outposts
