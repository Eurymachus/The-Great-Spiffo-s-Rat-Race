local EntertainmentSnapshot = {}

function EntertainmentSnapshot.copy(values)
    local result = {}
    for id, count in pairs(values or {}) do
        if count > 0 then result[id] = count end
    end
    return result
end

function EntertainmentSnapshot.observe(run)
    local state = run and run.entertainment
    assert(state and state.schema == nil and state.partial == nil, "unsupported_entertainment_state")
    return {
        literature = EntertainmentSnapshot.copy(state.literature),
    }
end

return EntertainmentSnapshot
