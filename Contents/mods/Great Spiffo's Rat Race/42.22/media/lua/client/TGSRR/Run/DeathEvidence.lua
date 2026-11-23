local StartingLocation = require("TGSRR/Run/StartingLocation")

local WoundEvidence = require("TGSRR/Run/WoundEvidence")

local DeathEvidence = {}
local WINDOW_MS = 10000
local MAX_SOURCES = 32
local activeRun, activePlayer
local recent = {}
local serial = 0
local installed = false
local thermalLevel, thermalStage, thermalAt, thermalUtc, thermalWorldAge

local function finite(value)
    return type(value) == "number" and value == value
        and value > -math.huge and value < math.huge
end

local function observeSickness(player)
    local body = player:getBodyDamage()
    local stats = player:getStats()
    if not body or not stats then return nil end
    return {
        foodSickness = stats:get(CharacterStat.FOOD_SICKNESS),
        poison = stats:get(CharacterStat.POISON),
        corpseSicknessRate = player:getCorpseSicknessRate(),
        woundInfectionLevel = body:getGeneralWoundInfectionLevel(),
    }
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
    recent[source] = { at = now, amount = amount, serial = serial,
        sickness = (source == "SICK" or source == "POISON")
            and observeSickness(player) or nil }
end

local function observeLivingThermal(player)
    if player ~= activePlayer or not activeRun or activeRun.lifecycle ~= "active"
        or player:isDead() then return end
    WoundEvidence.observe(player)
    local body, moodles = player:getBodyDamage(), player:getMoodles()
    if not body or not moodles then return end
    -- Scalars only: retain the latest living sample, including recovery to level zero.
    thermalLevel = moodles:getMoodleLevel(MoodleType.HYPOTHERMIA)
    thermalStage = body:getColdDamageStage()
    thermalAt = getTimestampMs()
    thermalUtc = getTimestamp()
    thermalWorldAge = getGameTime():getWorldAgeHours()
end

function DeathEvidence.initialize(run, player)
    -- Initialization/recovery begins a fresh observation window, even for the same run.
    recent, serial = {}, 0
    activeRun, activePlayer = run, player
    thermalLevel, thermalStage, thermalAt, thermalUtc, thermalWorldAge = nil, nil, nil, nil, nil
    WoundEvidence.reset()
    if player and not player:isDead() then WoundEvidence.observe(player, true) end
    observeLivingThermal(player)
    if not installed then
        Events.OnPlayerGetDamage.Add(observeDamage)
        Events.OnPlayerUpdate.Add(observeLivingThermal)
        installed = true
    end
end

function DeathEvidence.capture(player, context)
    local evidence = {
        schema = 4,
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
        evidence.terminalWounds = WoundEvidence.observe(player, player ~= activePlayer)
        evidence.sickness = observeSickness(player)
        local stats = player:getStats()
        if stats then
            -- Engine burden, not a count of doses or proof of fatal causation.
            evidence.medication = {
                sleepingPillsTaken = player:getSleepingPillsTaken(),
                intoxication = stats:get(CharacterStat.INTOXICATION),
            }
        end
        local bodyDamage = player:getBodyDamage()
        if bodyDamage then
            evidence.infectedAtDeath = bodyDamage:isInfected() == true
            evidence.thermalDamageStageAtDeath = bodyDamage:getColdDamageStage()
        end
    end
    if context == "death_callback" and player == activePlayer then
        local now = getTimestampMs()
        if thermalAt and now >= thermalAt then
            evidence.lastLivingThermal = {
                hypothermiaLevel = thermalLevel, damageStage = thermalStage,
                observedUtc = thermalUtc, observedWorldAgeHours = thermalWorldAge,
                ageMilliseconds = math.floor(now - thermalAt),
            }
        end
        local ordered = {}
        for source, entry in pairs(recent) do
            local age = now - entry.at
            if age >= 0 and age <= WINDOW_MS then
                ordered[#ordered + 1] = { source = source, amount = entry.amount,
                    ageMilliseconds = math.floor(age), serial = entry.serial, sickness = entry.sickness }
            end
        end
        table.sort(ordered, function(a, b) return a.serial < b.serial end)
        for _, entry in ipairs(ordered) do
            evidence.recentDamage[#evidence.recentDamage + 1] = {
                source = entry.source, amount = entry.amount,
                ageMilliseconds = entry.ageMilliseconds,
                sickness = entry.sickness,
            }
            evidence.lastDamageSource = entry.source
        end
    end
    local living = evidence.lastLivingThermal
    local fatalHypothermia = living and living.hypothermiaLevel == 4
        and living.ageMilliseconds <= 1000 and living.damageStage > 0
        and living.damageStage < 1 and evidence.thermalDamageStageAtDeath == 1
        and evidence.lastDamageSource == ""
    local fatalPills = evidence.medication and evidence.medication.sleepingPillsTaken >= 12
    local pillsWithBleeding = false
    if evidence.medication and evidence.medication.sleepingPillsTaken >= 10 then
        for _, observation in ipairs(evidence.recentDamage) do
            if observation.source == "BLEEDING" then
                pillsWithBleeding = true
                break
            end
        end
    end
    local competingPills = fatalPills and (evidence.killedByFall or evidence.deathDragDown
        or evidence.lastDamageSource ~= "" or evidence.thermalDamageStageAtDeath == 1)
    -- Both flags remain available even if they conflict. Never invent a winner.
    if evidence.killedByFall and evidence.deathDragDown then
        evidence.cause, evidence.certainty = "mixed", "conflicting_flags"
    elseif competingPills or pillsWithBleeding then
        -- Competing observations do not establish which mechanism finished the death.
        evidence.cause, evidence.certainty = "mixed", "competing_evidence"
    elseif evidence.killedByFall then
        evidence.cause, evidence.certainty = "fall", "explicit_flag"
    elseif evidence.deathDragDown then
        evidence.cause, evidence.certainty = "zombie_drag_down", "explicit_flag"
    elseif fatalPills then
        if evidence.killedByFall == false and evidence.deathDragDown == false
            and evidence.thermalDamageStageAtDeath ~= nil then
            evidence.cause, evidence.certainty = "sleeping_pills", "fatal_threshold"
        end
    elseif fatalHypothermia then
        evidence.cause, evidence.certainty = "hypothermia", "fatal_threshold"
    elseif evidence.lastDamageSource ~= "" then
        evidence.cause = evidence.lastDamageSource
        evidence.certainty = "suspected"
        if evidence.lastDamageSource == "BLEEDING"
            and WoundEvidence.supportsZombieBleeding(evidence.terminalWounds) then
            evidence.cause = "zombie_attack"
        end
        if evidence.lastDamageSource == "SICK" then
            for _, observation in ipairs(evidence.recentDamage) do
                if observation.source == "POISON" then
                    -- Poison also raises sickness; retain callback order separately.
                    evidence.cause = "POISON"
                    break
                end
            end
        end
    end
    return evidence
end

return DeathEvidence
