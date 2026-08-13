local Locations = require "TGSRR/Locations/Registry"

local function landmark(id, name, area, category, buildingIds, x, y, z)
    Locations.add({
        id = id,
        name = name,
        area = area,
        category = category,
        buildingIds = buildingIds,
        anchor = { x = x, y = y, z = z or 0 },
        optional = true,
    })
end

landmark("star_eplex_cinema", "StarEplex Cinema", "Valley Station",
    "Entertainment", { "6192677120901126" }, 13637, 5887, 0)
landmark("twiggys", "Twiggy's", "West Point",
    "Entertainment", { "7318551257939979" }, 12067, 6802, 0)
landmark("fossoil_hq", "Fossoil Headquarters", "Louisville",
    "Corporate", { "1689051723726860" }, 12083, 1605, 0)
landmark("gas2go_facility", "Gas2Go Facility", "Louisville",
    "Industrial", {
        "1407576747016211", "1407576747016212", "1407576747016226",
    }, 12071, 1435, 0)
landmark("gigamart_hq", "Gigamart Headquarters", "Louisville",
    "Corporate", { "1689060313661461" }, 12644, 1685, 0)
landmark("big_spiffos", "Big Spiffo's", "Louisville",
    "Spiffo", { "3940855832379393" }, 12435, 3784, 0)
landmark("spiffos_hq", "Spiffo's Headquarters", "Louisville",
    "Spiffo", { "1689060313661459" }, 12708, 1607, 1)
landmark("scarlet_oak_distillery", "Scarlet Oak Distillery", "Louisville",
    "Industrial", { "1970522405470208" }, 12015, 2040, 0)
landmark("scarlett_oak_airport", "Scarlett Oak Airport Distillery", "Louisville",
    "Industrial", { "3377953123598339" }, 15307, 3259, 0)
landmark("knox_distillery", "Knox Distillery", "Louisville",
    "Industrial", { "1407589631918092" }, 12906, 1368, 0)
landmark("grand_ohio_mall", "Grand Ohio Mall", "Louisville",
    "Shopping", { "1126123245142018" }, 13623, 1365, 0)
landmark("wheat_dream_factory", "The Wheat Dream Factory", "Louisville",
    "Industrial", { "3377953123598337" }, 15351, 3150, 1)
landmark("cockayne_inc", "Cockayne Inc.", "Louisville",
    "Industrial", { "3377957418565636" }, 15488, 3079, 0)
landmark("wizards_keep", "The Wizard's Keep", "Irvington",
    "Entertainment", { "16044099442311170" }, 1760, 14784, 0)
landmark("doe_valley_bunker", "Bunker", "Doe Valley Forest",
    "Remote", { "10133189355896832" }, 5576, 9365, -1)
landmark("muldraugh_radio_tower", "Radio Tower", "Muldraugh",
    "Infrastructure", { "9570321006854147" }, 10253, 8734, 0)
landmark("riverside_radio_tower", "Radio Tower", "Riverside",
    "Infrastructure", { "6755476750467072" }, 4833, 6279, 0)
landmark("brandenburg_detention_center", "Detention Centre",
    "Brandenburg", "Civic", { "6192470962470913" }, 1411, 5899, 0)
landmark("mccoy_estate", "McCoy Estate", "Muldraugh",
    "Estate", { "9007366758465536" }, 10086, 8261, 1)
landmark("fallas_luxury_cabins", "Remote Luxury Cabins",
    "Fallas Lake", "Remote", { "8162877403824129" }, 6367, 7620, 2)
landmark("airport_atc_tower", "Airport ATC Tower", "Louisville",
    "Infrastructure", { "2815003170177024" }, 15361, 2669, 8)

-- Increment whenever the canonical landmark membership changes. Existing runs
-- then disclose that visits before the change may be incomplete.
Locations.setVersion(1)

return Locations
