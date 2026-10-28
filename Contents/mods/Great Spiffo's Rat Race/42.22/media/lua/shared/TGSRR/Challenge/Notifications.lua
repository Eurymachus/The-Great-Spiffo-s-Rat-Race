local Notifications = {}
local listeners = {}

function Notifications.subscribe(id, callback)
    if type(id) ~= "string" or type(callback) ~= "function" then return false end
    listeners[id] = callback
    return true
end

function Notifications.unsubscribe(id)
    listeners[id] = nil
end

function Notifications.emit(outpostId, deliverableId)
    for _, callback in pairs(listeners) do
        callback(outpostId, deliverableId)
    end
end

return Notifications
