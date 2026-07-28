local sourceRoot = "Contents/mods/Great Spiffo's Rat Race/42.19/media/lua/"
package.path = sourceRoot .. "shared/?.lua;" .. package.path

local persisted = {}
ModData = {
    getOrCreate = function(key)
        persisted[key] = persisted[key] or {}
        return persisted[key]
    end,
}

local monthDays = {
    31, 28, 31, 30, 31, 30,
    31, 31, 30, 31, 30, 31,
}

local function leapYear(year)
    return year % 4 == 0
        and (year % 100 ~= 0 or year % 400 == 0)
end

local gameTime = {
    today = 0,
    helicopterDay = 6,
    helicopterStartHour = 15,
    helicopterEndHour = 18,
}

function gameTime:getNightsSurvived() return self.today end
function gameTime:getHelicopterDay() return self.helicopterDay end
function gameTime:getHelicopterStartHour()
    return self.helicopterStartHour
end
function gameTime:getHelicopterEndHour()
    return self.helicopterEndHour
end
function gameTime:setHelicopterDay(value) self.helicopterDay = value end
function gameTime:setHelicopterStartHour(value)
    self.helicopterStartHour = value
end
function gameTime:setHelicopterEndHour(value)
    self.helicopterEndHour = value
end
function gameTime:getStartYear() return 1993 end
function gameTime:getStartMonth() return 6 end
function gameTime:getStartDay() return 8 end
function gameTime:daysInMonth(year, month)
    if month == 1 and leapYear(year) then return 29 end
    return monthDays[month + 1]
end

function getGameTime() return gameTime end

SandboxVars = {
    TGSRRHelicopter = {
        Enabled = true,
        Year1Months = "",
        Year2Months = "7,1",
        Year3Months = "7,11,3",
        Year4Months = "7,10,1,4",
        Year5Months = "7,9,11,1,3",
        Year6Months = "7,10,1,4",
        Year7Months = "7,11,3",
        Year8Months = "7,1",
        Year9Months = "7",
        DayMinimum = 8,
        DayMaximum = 14,
        StartHourMinimum = 9,
        StartHourMaximum = 18,
        DurationMinimum = 1,
        DurationMaximum = 4,
    },
}

local randomValues = {}
function ZombRand(minimum, maximum)
    local value = table.remove(randomValues, 1)
    assert(value ~= nil, "test random value missing")
    assert(value >= minimum and value < maximum,
        "test random value outside requested range")
    return value
end

local Scheduler = require "TGSRR/Core/HelicopterScheduler"
local BasicSchedule = require "TGSRR/Helicopter/BasicSchedule"
local options = {
    modDataKey = "TGSRR_HelicopterScheduler_Test",
    policy = BasicSchedule,
}

local state, status = Scheduler.update(options)
assert(status == "scheduled")
assert(state.initialVanilla.day == 6)
assert(gameTime.helicopterDay == 6)

gameTime.today = 7
randomValues = { 8, 9, 1 }
state, status = Scheduler.update(options)
assert(status == "scheduled_new")
assert(state.current.challengeYear == 2)
assert(state.current.calendarYear == 1994)
assert(state.current.month == 7)
assert(state.current.calendarDay == 8)
assert(state.current.day == 364)
assert(gameTime.helicopterDay == 364)
assert(gameTime.helicopterStartHour == 9)
assert(gameTime.helicopterEndHour == 10)

state, status = Scheduler.update(options)
assert(status == "scheduled")
assert(state.slotIndex == 1)

gameTime.today = 365
randomValues = { 14, 18, 4 }
state, status = Scheduler.update(options)
assert(status == "scheduled_new")
assert(state.current.challengeYear == 2)
assert(state.current.calendarYear == 1995)
assert(state.current.month == 1)
assert(state.current.calendarDay == 14)
assert(state.current.day == 554)
assert(gameTime.helicopterStartHour == 18)
assert(gameTime.helicopterEndHour == 22)

local leapDate = Scheduler.dateForDay(
    Scheduler.dayForDate(1996, 2, 29, gameTime),
    gameTime)
assert(leapDate.year == 1996)
assert(leapDate.month == 2)
assert(leapDate.day == 29)

local yearFive = BasicSchedule.monthsForYear(5)
assert(table.concat(yearFive, ",") == "7,9,11,1,3")
assert(#BasicSchedule.monthsForYear(10) == 0)

local alternate, alternateError = BasicSchedule.normalize({
    MonthsByYear = {
        [1] = { 8 },
        [2] = { 2, 6 },
    },
    DayMinimum = 3,
    DayMaximum = 5,
    StartHourMinimum = 11,
    StartHourMaximum = 12,
    DurationMinimum = 2,
    DurationMaximum = 2,
})
assert(alternate ~= nil, alternateError)
assert(#alternate.slots == 3)
assert(alternate.slots[1].challengeYear == 1)
assert(alternate.slots[1].month == 8)
assert(alternate.slots[3].challengeYear == 2)
assert(alternate.slots[3].month == 6)
assert(alternate.dayMinimum == 3)
assert(alternate.dayMaximum == 5)
assert(alternate.durationMinimum == 2)
assert(alternate.durationMaximum == 2)

gameTime.today = 0
randomValues = { 3, 11, 2 }
local alternateEvent, alternateEventError =
    BasicSchedule.chooseNext({
        slotIndex = 0,
        policyConfig = alternate,
    }, gameTime)
assert(alternateEvent ~= nil, alternateEventError)
assert(alternateEvent.challengeYear == 1)
assert(alternateEvent.calendarYear == 1993)
assert(alternateEvent.month == 8)
assert(alternateEvent.calendarDay == 3)
assert(alternateEvent.startHour == 11)
assert(alternateEvent.endHour == 13)

local registered, registeredError = BasicSchedule.fromRegistered({
    Enabled = true,
    Year1Months = " 8 ",
    Year2Months = "2, 6",
    Year3Months = "",
    Year4Months = "",
    Year5Months = "",
    Year6Months = "",
    Year7Months = "",
    Year8Months = "",
    Year9Months = "",
    DayMinimum = 3,
    DayMaximum = 5,
    StartHourMinimum = 11,
    StartHourMaximum = 12,
    DurationMinimum = 2,
    DurationMaximum = 2,
})
assert(registered ~= nil, registeredError)
assert(#registered.slots == 3)
assert(registered.monthsByYear[2][2] == 6)

local spaced, spacedError = BasicSchedule.fromRegistered({
    Enabled = true,
    Year1Months = "7 1",
})
assert(spaced == nil)
assert(spacedError == "invalid_helicopter_month")

local semicolon, semicolonError = BasicSchedule.fromRegistered({
    Enabled = true,
    Year1Months = "7;1",
})
assert(semicolon == nil)
assert(semicolonError == "invalid_helicopter_month")

gameTime.today = 0
gameTime.helicopterDay = 6
gameTime.helicopterStartHour = 15
gameTime.helicopterEndHour = 18
randomValues = { 10, 11, 2 }
local replacementPolicy = {
    id = "replacement_test",
    prepare = function() return true end,
    chooseNext = function()
        return {
            slotIndex = 1,
            challengeYear = 1,
            calendarYear = 1993,
            month = 7,
            calendarDay = 10,
            day = 1,
            startHour = 11,
            endHour = 13,
        }
    end,
}
local replaced, replacedStatus = Scheduler.update({
    modDataKey = "TGSRR_HelicopterScheduler_Replacement_Test",
    policy = replacementPolicy,
    replaceScheduleOnInitialize = true,
    gameTime = gameTime,
})
assert(replaced ~= nil)
assert(replacedStatus == "scheduled_new")
assert(replaced.initialVanilla.day == 6)
assert(gameTime.helicopterDay == 1)
assert(gameTime.helicopterStartHour == 11)
assert(gameTime.helicopterEndHour == 13)

print("helicopter scheduler test passed")
