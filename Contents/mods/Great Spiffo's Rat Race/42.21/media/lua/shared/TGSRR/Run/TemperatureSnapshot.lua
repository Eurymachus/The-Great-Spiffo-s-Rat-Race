local TemperatureSnapshot = {}

local function copyObservation(value)
    if not value then return nil end
    return {
        celsius = value.celsius,
        utc = value.utc,
        worldAgeHours = value.worldAgeHours,
        timeOfDay = value.timeOfDay,
        calendar = {
            year = value.calendar.year,
            month = value.calendar.month,
            day = value.calendar.day,
        },
    }
end

function TemperatureSnapshot.copy(state)
    if not state then return nil end
    return {
        schema = 1,
        unit = "celsius",
        source = "outdoor_weather",
        sampleIntervalGameMinutes = 1,
        partial = state.partial == true or nil,
        minimum = copyObservation(state.minimum),
        maximum = copyObservation(state.maximum),
    }
end

return TemperatureSnapshot
