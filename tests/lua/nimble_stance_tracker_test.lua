local recorderActive = true
local stopped = nil

package.loaded["TGSRR/Run/Recorder"] = {
    isActive = function() return recorderActive end,
    deactivate = function() recorderActive = false end,
}
package.loaded["TGSRR/Run/TrackingHealth"] = {
    stop = function(reason) stopped = reason end,
}

Events = {
    OnTick = { Add = function() end },
}

local gameSpeed = 1
function getGameSpeed() return gameSpeed end
function getTimestampMs() return 0 end

local state = {
    x = 10,
    y = 20,
    aiming = true,
    dead = false,
    vehicle = nil,
    fishing = false,
}
FishingState = {
    instance = function() return "fishing" end,
}
local player = {
    getX = function() return state.x end,
    getY = function() return state.y end,
    isAiming = function() return state.aiming end,
    isDead = function() return state.dead end,
    getVehicle = function() return state.vehicle end,
    isCurrentState = function(_, value)
        return value == "fishing" and state.fishing
    end,
}
local run = {
    nimbleStanceMovementMilliseconds = 0,
}

local Tracker = require "TGSRR/Run/NimbleStanceTracker"
assert(Tracker.initialize(run, player))

state.x = 10.1
Tracker.sample(100)
assert(run.nimbleStanceMovementMilliseconds == 100)

state.x = 10.2
state.aiming = false
Tracker.sample(200)
assert(run.nimbleStanceMovementMilliseconds == 100)

state.x = 10.3
state.aiming = true
Tracker.sample(300)
assert(run.nimbleStanceMovementMilliseconds == 100)
state.x = 10.4
Tracker.sample(400)
assert(run.nimbleStanceMovementMilliseconds == 200)

state.x = 10.5
state.vehicle = {}
Tracker.sample(500)
assert(run.nimbleStanceMovementMilliseconds == 200)
state.vehicle = nil

state.x = 10.6
state.fishing = true
Tracker.sample(600)
assert(run.nimbleStanceMovementMilliseconds == 200)
state.fishing = false

state.x = 10.7
gameSpeed = 0
Tracker.sample(700)
assert(run.nimbleStanceMovementMilliseconds == 200)
gameSpeed = 1

state.x = 10.8
Tracker.sample(2000)
assert(run.nimbleStanceMovementMilliseconds == 200)
state.x = 10.9
Tracker.sample(2100)
assert(run.nimbleStanceMovementMilliseconds == 300)

assert(stopped == nil)
print("nimble stance tracker test passed")
