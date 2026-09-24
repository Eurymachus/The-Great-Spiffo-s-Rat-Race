local Snapshot = {}

function Snapshot.observe(run, records)
    local stored = type(run) == "table" and run.outpostLifecycles or nil
    return {
        outposts = stored and type(stored.outposts) == "table"
            and stored.outposts or {},
        deliverables = stored and type(stored.deliverables) == "table"
            and stored.deliverables or {},
    }
end

return Snapshot
