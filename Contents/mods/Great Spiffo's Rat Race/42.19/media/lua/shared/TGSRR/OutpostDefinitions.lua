local Outposts = require "TGSRR/Outposts"

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

add("brandenburg", "Brandenburg", {2091, 6024, 0}, {2068, 6002, 2099, 6045}, {2083, 6023}, {
    building("6473958824083477"),
})

add("echo_creek", "Echo Creek", {3541, 11205, 0}, {3531, 11198, 3555, 11224}, {3541, 11211}, {
    building("12103479833133062", {
        excludeRoomIds = {
            "12103479833133143", -- inaccessible decorative bell tower
        },
    }),
})

add("ekron", "Ekron", {447, 9933, 0}, {438, 9913, 470, 9942}, {450, 9926}, {
    building("10696053409972226", { underground = true }),
    building("10696053409972268", {
        excludeRoomIds = {
            "10696053409972614", -- inaccessible decorative bell tower
            "10696053409972615", -- inaccessible decorative bell tower
        },
    }),
})

add("fallas_lake", "Fallas Lake", {7388, 8352, 0}, {7379, 8348, 7396, 8359}, {7387, 8353}, {
    building("9007319513825288"),
})

add("hog_wallow_military_base", "Hog Wallow Military Base", {5559, 12487, 0}, {5536, 12439, 5583, 12505}, {5560, 12472}, {
    building("13510889076424704", { underground = true }),
    building("13510889076424705"),
})

add("irvington", "Irvington", {2433, 14232, 0}, {2406, 14211, 2440, 14255}, {2423, 14233}, {
    building("15481162373791744", { underground = true }),
    building("15481162373791782", {
        excludeRoomIds = {
            "15481162373792021", -- inaccessible decorative bell tower
        },
    }),
})

add("louisville", "Louisville", {12609, 3370, 0}, {12599, 3351, 12618, 3384}, {12608, 3368}, {
    building("3659385150636034"),
})

add("march_ridge", "March Ridge", {10322, 12807, 0}, {10317, 12779, 10345, 12816}, {10331, 12797}, {
    building("13792445657513985"),
})

add("muldraugh", "Muldraugh", {10757, 10163, 0}, {10750, 10160, 10773, 10170}, {10761, 10165}, {
    building("10977700185374752", {
        excludeRoomIds = {
            "10977700185374947", -- inaccessible decorative bell tower
        },
    }),
})

add("riverside", "Riverside", {6579, 5377, 0}, {6555, 5362, 6583, 5383}, {6569, 5373}, {
    building("5629606908395526"),
})

add("rosewood", "Rosewood", {8127, 11550, 0}, {8117, 11536, 8144, 11562}, {8130, 11550}, {
    building("12666507095965713"),
})

add("valley_station", "Valley Station", {12850, 4952, 0}, {12843, 4949, 12869, 4965}, {12848, 4957}, {
    building("5348239305867264"),
    building("5348239305867265"),
})

add("west_point", "West Point", {11974, 6996, 0}, {11959, 6975, 11985, 7007}, {11972, 6991}, {
    building("7600021939683330"),
})

return Outposts
