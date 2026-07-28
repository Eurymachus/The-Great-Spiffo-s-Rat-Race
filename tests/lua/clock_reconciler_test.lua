package.loaded["TGSRR/Run/ClockCheckpoint"] = {
    initialize = function() return nil end,
}

local ClockReconciler = require "TGSRR/Run/ClockReconciler"

local function game(values)
    return {
        getYear = function() return values.year end,
        setYear = function(_, value) values.year = value end,
        getMonth = function() return values.month - 1 end,
        setMonth = function(_, value) values.month = value + 1 end,
        getDay = function() return values.day - 1 end,
        setDay = function(_, value) values.day = value + 1 end,
        getTimeOfDay = function() return values.timeOfDay end,
        setTimeOfDay = function(_, value) values.timeOfDay = value end,
        setLastTimeOfDay = function(_, value)
            values.lastTimeOfDay = value
        end,
        getNightsSurvived = function() return values.nightsSurvived end,
        setNightsSurvived = function(_, value)
            values.nightsSurvived = value
        end,
        getWorldAgeHours = function()
            local offset = values.timeOfDay >= 7
                and values.timeOfDay - 7
                or values.timeOfDay + 17
            return values.nightsSurvived * 24 + offset
        end,
    }
end

local run = {
    eventSequence = 20,
    eventHash = "abc",
}
local playerHours = 52
local player = {
    getHoursSurvived = function() return playerHours end,
}
local anchor = {
    eventSequence = 20,
    eventHash = "abc",
    calendar = { year = 1992, month = 12, day = 31 },
    timeOfDay = 23,
    nightsSurvived = 4,
    worldAgeHours = 112,
    playerHoursSurvived = 50,
}

local normalValues = {
    year = 1993,
    month = 1,
    day = 1,
    timeOfDay = 1,
    nightsSurvived = 4,
}
local normal = ClockReconciler.inspect(
    run, player, anchor, game(normalValues))
assert(normal.status == "consistent")
assert(normal.expected.worldAgeHours == 114)

local corruptValues = {
    year = 1993,
    month = 1,
    day = 1,
    timeOfDay = 9,
    nightsSurvived = 0,
}
anchor.calendar = { year = 1993, month = 1, day = 10 }
anchor.timeOfDay = 7
anchor.worldAgeHours = 96
anchor.playerHoursSurvived = 50
playerHours = 56
local corruptGame = game(corruptValues)
local corrupt = ClockReconciler.inspect(
    run, player, anchor, corruptGame)
assert(corrupt.status == "repair_required")
assert(corrupt.expected.calendar.year == 1993)
assert(corrupt.expected.calendar.month == 1)
assert(corrupt.expected.calendar.day == 10)
assert(corrupt.expected.timeOfDay == 13)
assert(corrupt.expected.worldAgeHours == 102)

local repaired, result = ClockReconciler.apply(corrupt, corruptGame)
assert(repaired, result)
assert(corruptValues.year == 1993)
assert(corruptValues.month == 1)
assert(corruptValues.day == 10)
assert(corruptValues.timeOfDay == 13)
assert(corruptValues.lastTimeOfDay == 13)
assert(corruptGame:getWorldAgeHours() == 102)

local mismatch = ClockReconciler.inspect({
    eventSequence = 19,
    eventHash = "def",
}, player, anchor, corruptGame)
assert(mismatch.status == "checkpoint_cursor_mismatch")

playerHours = 40
local ambiguous = ClockReconciler.inspect(
    run, player, anchor, corruptGame)
assert(ambiguous.status == "ambiguous")
assert(ambiguous.reason == "player_hours_regressed")

local leap = ClockReconciler.addDays(
    { year = 1992, month = 2, day = 28 }, 2)
assert(leap.year == 1992 and leap.month == 3 and leap.day == 1)

print("clock reconciler test passed")
