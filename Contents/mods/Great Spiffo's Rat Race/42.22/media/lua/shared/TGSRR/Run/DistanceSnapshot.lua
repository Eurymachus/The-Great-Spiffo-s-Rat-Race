local DistanceSnapshot = {}
function DistanceSnapshot.copy(value)
    if not value then return nil end
    return { onFoot = value.onFoot or 0, driver = value.driver or 0 }
end
function DistanceSnapshot.delta(value, baseline)
    if not value then return nil end
    baseline = baseline or {}
    return { onFoot = math.max(0, value.onFoot - (baseline.onFoot or 0)),
        driver = math.max(0, value.driver - (baseline.driver or 0)) }
end
return DistanceSnapshot
