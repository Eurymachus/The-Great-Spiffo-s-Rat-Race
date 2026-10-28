local Identity = require("TGSRR/Run/Identity")
local Recorder = require("TGSRR/Run/Recorder")
local TrackingHealth = require("TGSRR/Run/TrackingHealth")

local TemperatureTracker = {}
local activeRun
local installed = false

local function update(state, observation)
    -- Strict comparisons preserve the first occurrence of equal extremes.
    if not state.minimum or observation.celsius < state.minimum.celsius then
        state.minimum = observation
    end
    if not state.maximum or observation.celsius > state.maximum.celsius then
        state.maximum = observation
    end
end

function TemperatureTracker.sample()
    local run = activeRun
    if not run or run.lifecycle ~= "active" or not Recorder.isActive() then return end
    local daily = run.dailyState
    if not daily then return end
    -- Global climate excludes room, vehicle, local fire and wind-chill effects.
    local celsius = getClimateManager():getTemperature()
    if type(celsius) ~= "number" or celsius ~= celsius
            or celsius == math.huge or celsius == -math.huge then
        run.integrityStatus = "invalid_outdoor_temperature"
        TrackingHealth.stop(run.integrityStatus, "Temperature tracking failed.")
        error("invalid_outdoor_temperature")
    end
    local gameTime = getGameTime()
    local observation = {
        celsius = celsius,
        utc = Identity.utcSeconds(),
        worldAgeHours = gameTime:getWorldAgeHours(),
        timeOfDay = gameTime:getTimeOfDay(),
        calendar = {
            year = gameTime:getYear(),
            month = gameTime:getMonth() + 1,
            day = gameTime:getDay() + 1,
        },
    }
    daily.outdoorTemperature = daily.outdoorTemperature or {}
    update(daily.outdoorTemperature, observation)
    update(run.outdoorTemperature, observation)
end

function TemperatureTracker.initialize(run, created)
    activeRun = run
    if not run.outdoorTemperature then
        run.outdoorTemperature = {
            partial = not created or run.bootstrapped == true,
        }
        if run.dailyState then
            run.dailyState.outdoorTemperature = {
                partial = not created or run.bootstrapped == true,
            }
        end
    end
    if not installed then
        installed = true
        -- DayTracker's EveryDays handler seals the old day before this event.
        Events.EveryOneMinute.Add(TemperatureTracker.sample)
    end
    TemperatureTracker.sample()
end

return TemperatureTracker
