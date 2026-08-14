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
local paused = false
local now = 0
function getGameSpeed() return gameSpeed end
function isGamePaused() return paused end
function getTimestampMs() return now end

local menuVisible = false
MainScreen = {
    instance = {
        inGame = true,
        getIsVisible = function() return menuVisible end,
    },
}
UIManager = {
    getSpeedControls = function()
        return {
            getCurrentGameSpeed = function() return gameSpeed end,
        }
    end,
}

local player = {}
local run = {
    activeGameplayMilliseconds = 0,
}

local Tracker = require "TGSRR/Run/ActiveGameplayTracker"
assert(Tracker.initialize(run, player))

Tracker.sample(100)
assert(run.activeGameplayMilliseconds == 100)

paused = true
Tracker.sample(200)
assert(run.activeGameplayMilliseconds == 100)
paused = false

menuVisible = true
Tracker.sample(300)
assert(run.activeGameplayMilliseconds == 100)
menuVisible = false

gameSpeed = 0
Tracker.sample(400)
assert(run.activeGameplayMilliseconds == 100)
gameSpeed = 4
Tracker.sample(500)
assert(run.activeGameplayMilliseconds == 200)

Tracker.sample(6000)
assert(run.activeGameplayMilliseconds == 200)
Tracker.sample(6100)
assert(run.activeGameplayMilliseconds == 300)

assert(stopped == nil)
print("active gameplay tracker test passed")
