local StartingLocation = require("TGSRR/Run/StartingLocation")

local DeathEvidence = {}
local WINDOW_MS = 10000
local MAX_SOURCES = 32
local activeRun, activePlayer
local recent = {}
local serial = 0
local installed = false

local function finite(value)
    return type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function observeDamage(player, source, amount)
    if player ~= activePlayer or not activeRun
        or activeRun.lifecycle ~= "active" then return end
    if type(source) ~= "string" or source == "" or #source > 64
        or not finite(amount) or amount <= 0 then return end
    local now = getTimestampMs()
    local count, oldestSource, oldestSerial = 0, nil, math.huge
    for key, entry in pairs(recent) do
        if now < entry.at or now - entry.at > WINDOW_MS then
            recent[key] = nil
        else
            count = count + 1
            if entry.serial < oldestSerial then
                oldestSource, oldestSerial = key, entry.serial
            end
        end
    end
    if not recent[source] and count >= MAX_SOURCES then
        recent[oldestSource] = nil
    end
    serial = serial + 1
    recent[source] = { at = now, amount = amount, serial = serial }
end

function DeathEvidence.initialize(run, player)
    -- Initialization/recovery begins a fresh observation window, even for the same run.
    recent, serial = {}, 0
    activeRun, activePlayer = run, player
    if not installed then
        Events.OnPlayerGetDamage.Add(observeDamage)
        installed = true
    end
end

function DeathEvidence.capture(player, context)
    local evidence = {
        schema = 1,
        captureContext = context or "recovery",
        recentWindowMilliseconds = WINDOW_MS,
        recentDamage = {},
        lastDamageSource = "",
        cause = "unknown",
        certainty = "unknown",
    }
    if not player then return evidence end
    local x, y, z = player:getX(), player:getY(), player:getZ()
    if finite(x) and finite(y) and finite(z) then
        -- Reuse registered location matching, without fabricating missing coordinates.
        evidence.location = StartingLocation.observe(player, getTimestamp(),
            getGameTime():getWorldAgeHours(), context ~= "death_callback")
    end
    evidence.killedByFall = player:isKilledByFall() == true
    evidence.deathDragDown = player:isDeathDragDown() == true
    if context == "death_callback" then
        local bodyDamage = player:getBodyDamage()
        if bodyDamage then
            evidence.infectedAtDeath = bodyDamage:isInfected() == true
        end
    end
    if context == "death_callback" and player == activePlayer then
        local now = getTimestampMs()
        local ordered = {}
        for source, entry in pairs(recent) do
            local age = now - entry.at
            if age >= 0 and age <= WINDOW_MS then
                ordered[#ordered + 1] = { source = source, amount = entry.amount,
                    ageMilliseconds = math.floor(age), serial = entry.serial }
            end
        end
        table.sort(ordered, function(a, b) return a.serial < b.serial end)
        for _, entry in ipairs(ordered) do
            evidence.recentDamage[#evidence.recentDamage + 1] = {
                source = entry.source, amount = entry.amount,
                ageMilliseconds = entry.ageMilliseconds,
            }
            evidence.lastDamageSource = entry.source
        end
    end
    -- Both flags remain available even if they conflict. Never invent a winner.
    if evidence.killedByFall and evidence.deathDragDown then
        evidence.cause, evidence.certainty = "mixed", "conflicting_flags"
    elseif evidence.killedByFall then
        evidence.cause, evidence.certainty = "fall", "explicit_flag"
    elseif evidence.deathDragDown then
        evidence.cause, evidence.certainty = "zombie_drag_down", "explicit_flag"
    elseif evidence.lastDamageSource ~= "" then
        evidence.cause = evidence.lastDamageSource
        evidence.certainty = "suspected"
    end
    return evidence
end

return DeathEvidence
