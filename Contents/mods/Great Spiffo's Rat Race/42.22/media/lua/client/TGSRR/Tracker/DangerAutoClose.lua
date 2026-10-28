local DangerAutoClose = {}

function DangerAutoClose.isEnabled()
    local options = SandboxVars and SandboxVars.TGSRRTracker or nil
    return not options or options.DangerAutoClose ~= false
end

function DangerAutoClose.shouldClose(player)
    if not DangerAutoClose.isEnabled() or not player or not player.getStats then
        return false
    end
    local stats = player:getStats()
    if not stats then return false end

    -- Match vanilla Search Mode's zombie-danger conditions.
    if stats:getNumVeryCloseZombies() > 0 then return true end
    return stats:getNumVisibleZombies() >= 3
        and stats:getNumChasingZombies() >= 3
end

return DangerAutoClose
