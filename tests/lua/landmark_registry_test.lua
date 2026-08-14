local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

local Locations = require "TGSRR/Locations/Definitions"

assert(Locations.getVersion() == 1)
assert(#Locations.getAll() == 21)

local cinema = Locations.findByBuildingId("6192677120901126")
assert(cinema and cinema.id == "star_eplex_cinema")
assert(cinema.name == "StarEplex Cinema")

local gas2goA = Locations.findByBuildingId("1407576747016211")
local gas2goB = Locations.findByBuildingId("1407576747016212")
local gas2goC = Locations.findByBuildingId("1407576747016226")
assert(gas2goA and gas2goA == gas2goB and gas2goB == gas2goC)
assert(gas2goA.id == "gas2go_facility")

assert(Locations.findByBuildingId("missing") == nil)

local mccoyEstate = Locations.findByBuildingId("9007366758465536")
assert(mccoyEstate and mccoyEstate.id == "mccoy_estate")
assert(mccoyEstate.name == "McCoy Estate")
assert(mccoyEstate.category == "Estate")

local Snapshot = require "TGSRR/Run/LocationSnapshot"
local snapshot = Snapshot.observe({
    locations = {
        registryVersion = 1,
        visits = {
            star_eplex_cinema = {
                utc = 123,
                worldAgeHours = 45.5,
                buildingId = "6192677120901126",
                discoveryMethod = "building",
                x = 13637,
                y = 5887,
            },
        },
    },
})
assert(snapshot.schema == 2)
assert(snapshot.registryVersion == 1)
assert(#snapshot.entries == 21)
assert(snapshot.entries[1].id == "star_eplex_cinema")
assert(snapshot.entries[1].visited == true)
assert(snapshot.entries[1].firstVisit.buildingId == "6192677120901126")
assert(snapshot.entries[1].optional == true)

print("landmark registry test passed")
