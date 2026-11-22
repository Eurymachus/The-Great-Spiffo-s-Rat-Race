local Snapshot = {}
function Snapshot.copy(values)
    local result = {}
    for id, count in pairs(values or {}) do
        if count > 0 then result[id] = count end
    end
    return result
end
function Snapshot.observe(run)
    local state = run and run.farming
    if not state then return nil end
    return {schema = 1, planted = Snapshot.copy(state.planted),
        harvested = Snapshot.copy(state.harvested), produce = Snapshot.copy(state.produce),
        partial = state.partial == true or nil}
end
return Snapshot
