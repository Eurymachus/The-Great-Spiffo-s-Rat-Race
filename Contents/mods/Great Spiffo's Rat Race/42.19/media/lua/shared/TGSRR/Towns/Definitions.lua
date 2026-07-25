local Towns = require "TGSRR/Towns/Registry"

local DEFAULT_RADIUS = 200

local function point(id, x, y, radius)
    return { id = id, x = x, y = y, radius = radius or DEFAULT_RADIUS }
end

local function add(id, points)
    return Towns.add({ id = id, points = points })
end

add("brandenburg", {
    point("centre", 2101, 6076),
})

add("echo_creek", {
    point("north", 3518, 10926, 250),
    point("south", 3542, 11207, 250),
})

add("ekron", {
    point("north_centre", 545, 9754, 220),
    point("south_west", 444, 9928, 220),
    point("east", 790, 9835, 220),
})

add("fallas_lake", {
    point("centre", 7276, 8345),
})

add("irvington", {
    point("centre", 2498, 14253),
})

add("louisville", {
    point("north_west", 12230, 1320, 350),
    point("north_centre_west", 12790, 1210, 350),
    point("north_centre", 13160, 1520, 350),
    point("north_east", 13570, 1310, 350),
    point("west_centre", 12350, 1760, 350),
    point("centre", 12970, 2230, 350),
    point("east_centre", 13690, 1770, 350),
    point("west_riverside", 12030, 2590, 350),
    point("west_south", 12430, 2820, 350),
    point("centre_south", 13040, 2820, 350),
    point("east_south", 13780, 2550, 350),
    point("far_east_south", 14150, 2610, 350),
    point("south_west", 12510, 3350, 350),
    point("south_centre", 13210, 3080, 350),
    point("south_east", 13940, 3040, 350),
    point("south_checkpoint", 12510, 4190, 350),
})

add("march_ridge", {
    point("west", 10121, 12720, 250),
    point("east", 10331, 12797, 250),
})

add("muldraugh", {
    point("north", 10782, 9950, 250),
    point("south", 10761, 10165, 250),
})

add("riverside", {
    point("west", 6443, 5281, 250),
    point("east", 6569, 5373, 250),
})

add("rosewood", {
    point("centre", 8107, 11576),
})

add("valley_station", {
    point("west_north", 12734, 5033, 300),
    point("centre", 13515, 5082, 300),
    point("east_south", 13734, 5643, 300),
    point("west_south", 12733, 5773, 300),
})

add("west_point", {
    point("west", 11697, 6834, 250),
    point("east", 11972, 6991, 250),
})

return Towns
