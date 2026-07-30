local EventsBus = {}
local listeners = {}

function EventsBus.subscribe(eventName, listenerId, callback)
    if not eventName or not listenerId or type(callback) ~= "function" then return false end
    listeners[eventName] = listeners[eventName] or {}
    listeners[eventName][listenerId] = callback
    return true
end

function EventsBus.unsubscribe(eventName, listenerId)
    local eventListeners = listeners[eventName]
    if eventListeners then eventListeners[listenerId] = nil end
end

local function dispatch(eventName, payload)
    local eventListeners = listeners[eventName]
    if not eventListeners then return end
    for _, callback in pairs(eventListeners) do pcall(callback, payload) end
end

function EventsBus.emit(eventName, payload)
    payload = payload or {}
    payload.name = eventName
    dispatch(eventName, payload)
    dispatch("*", payload)
    return payload
end

return EventsBus
