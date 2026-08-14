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
        local ok, reason = pcall(callback, outpostId, deliverableId)
        if not ok then print("TGSRR deliverable notification failed: " .. tostring(reason)) end
    end
end

return Notifications
