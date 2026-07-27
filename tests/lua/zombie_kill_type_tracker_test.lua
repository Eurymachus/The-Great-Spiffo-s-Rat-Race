local updateHandler = nil
local hitHandler = nil

Events = {
    OnZombieUpdate = {
        Add = function(handler) updateHandler = handler end,
    },
    OnHitZombie = {
        Add = function(handler) hitHandler = handler end,
    },
}

function isDebugEnabled() return false end

local Tracker = require "TGSRR/Run/ZombieKillTypeTracker"

local run = { zombieKillTypes = {} }
local player = {}
Tracker.initialize(run, player)

local function zombie()
    local state = {
        data = {},
        variables = {},
        prone = false,
        gettingUp = false,
        onFront = false,
    }
    local value = {
        getModData = function() return state.data end,
        getVariableBoolean = function(_, name)
            return state.variables[name] == true
        end,
        isProne = function() return state.prone end,
        isGettingUp = function() return state.gettingUp end,
        isFallOnFront = function() return state.onFront end,
    }
    return value, state
end

local standing = zombie()
assert(Tracker.record(standing) == "standing")

local front, frontState = zombie()
frontState.prone = true
frontState.onFront = true
assert(Tracker.record(front) == "onfront")

local back, backState = zombie()
backState.prone = true
assert(Tracker.record(back) == "onback")

local fence, fenceState = zombie()
fenceState.variables.ClimbFenceStarted = true
hitHandler(fence, player)
assert(fenceState.data[Tracker.TAG_KEY] == "fenceAssist")
fenceState.variables.ClimbFenceStarted = false
fenceState.prone = true
updateHandler(fence)
assert(fenceState.data[Tracker.TAG_KEY] == "fenceAssist")
assert(Tracker.record(fence) == "fenceAssist")
assert(fenceState.data[Tracker.TAG_KEY] == nil)

local window, windowState = zombie()
windowState.variables.ClimbWindowFlopped = true
updateHandler(window)
assert(windowState.data[Tracker.TAG_KEY] == "windowAssist")
windowState.variables.ClimbWindowFlopped = false
windowState.gettingUp = true
updateHandler(window)
assert(windowState.data[Tracker.TAG_KEY] == "windowAssist")
windowState.gettingUp = false
updateHandler(window)
assert(windowState.data[Tracker.TAG_KEY] == nil)

assert(run.zombieKillTypes.standing == 1)
assert(run.zombieKillTypes.onfront == 1)
assert(run.zombieKillTypes.onback == 1)
assert(run.zombieKillTypes.fenceAssist == 1)
assert(run.zombieKillTypes.windowAssist == 0)

print("zombie kill type tracker test passed")
