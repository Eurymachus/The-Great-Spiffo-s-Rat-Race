local Locations = require "TGSRR/Locations/Registry"

-- Location membership is intentionally deferred. Increment this version whenever
-- the canonical definition set changes so existing runs disclose partial history.
Locations.setVersion(0)

return Locations
