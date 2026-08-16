local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.20/media/lua/"
package.path = sourceRoot .. "client/?.lua;"
    .. sourceRoot .. "shared/?.lua;"
    .. package.path

local openedPath = nil
local written = {}

function getFileReader()
    return nil
end

function getFileWriter(filename, createIfNull, append)
    openedPath = filename
    assert(createIfNull == true)
    assert(append == false)
    return {
        write = function(_, value)
            written[#written + 1] = value
        end,
        close = function() end,
    }
end

local FileStore = require "TGSRR/Run/FileStore"
local ok, status = FileStore.initialize({
    runId = "rr-test",
    createdUtc = "2026-07-29T00:00:00Z",
    createdWorldAgeHours = 0,
    bootstrapped = false,
    lifecycle = "active",
    epoch = 1,
    startingChallenge = {
        id = "TGSRR",
        gameMode = "The Great Spiffo's Rat Race",
    },
    startingChallengePartial = false,
    chosenStartingRegion = {
        schema = 1,
        selectionMode = "random",
        resolvedRegionId = "Rosewood, KY",
        capturedUtc = 1786819000,
    },
    startingCharacter = {
        forename = "Test",
        surname = "Rat",
        displayName = "Test Rat",
        professionId = "unemployed",
    },
}, true)

assert(ok == true)
assert(status == "created")
assert(openedPath == "TGSRR/Runs/rr-test/run.meta.txt")
assert(#written > 0)
local output = table.concat(written)
assert(output:find("chosenStartingRegionMode=random", 1, true))
assert(output:find("chosenStartingRegionId=Rosewood%2C KY", 1, true))
assert(output:find("chosenStartingRegionCapturedUtc=1786819000", 1, true))

print("file_store_test: ok")
