local Outposts = require "TGSRR/Outposts/Definitions"
local Store = require "TGSRR/Outposts/ProgressStore"
local Notifications = require "TGSRR/Challenge/Notifications"
local Completion = require "TGSRR/Outposts/Completion"
local ChallengeEvents = require "TGSRR/Core/Events"
require "TGSRR/Milestones/Definitions"
require "TGSRR/Outposts/Checks/RoomActivation"
require "TGSRR/Outposts/Checks/GroundFloorWindows"
require "TGSRR/Outposts/Checks/Enclosure"
require "TGSRR/Outposts/Checks/Fixtures"
local VehicleCheck = require "TGSRR/Outposts/Checks/Vehicle"
local ChallengeContext = require "TGSRR/Challenge/Context"

local Runtime = {}
local FALLBACK_INTERVAL_MS = 1000
local CERTIFICATION_GRACE_MS = 10000
local BASELINE_SETTLE_MS = 10000
local VEHICLE_LATCH_STREAM_GRACE_MS = 10000

local activeOutpost = nil
local lastRoom = nil
local lastPlayerX = nil
local lastPlayerY = nil
local nextFallbackAt = 0
local canCertifyAt = 0
local canSealBaselineAt = 0
local canValidateMissingLatchedVehicleAt = 0
local evaluationPending = false
local updateDeliverable
local observedEngineStates = {}
local observedStartingStates = {}
local armedEngineStarts = {}

local function markDiscovered(outpost)
    return Store.markDiscovered(outpost.id)
end

local function countZombies(outpost)
    local cell = getCell()
    local zombies = cell and cell:getZombieList() or nil
    if not zombies then return nil end

    local minX, minY, maxX, maxY = Outposts.getClearanceBounds(outpost)
    local count = 0
    for index = 0, zombies:size() - 1 do
        local zombie = zombies:get(index)
        if zombie and not zombie:isDead()
                and zombie:getX() >= minX and zombie:getX() <= maxX
                and zombie:getY() >= minY and zombie:getY() <= maxY then
            count = count + 1
        end
    end
    return count
end

function Runtime.evaluate(outpost, player)
    if not ChallengeContext.isActive() or not outpost or not player then
        return nil
    end
    markDiscovered(outpost)

    local inspection = Outposts.inspect(outpost, {
        player = player,
        includeWindowSurvey = true,
    })
    local activation = inspection.checks and inspection.checks.room_activation or nil
    local windows = inspection.checks and inspection.checks.ground_floor_windows or nil
    local enclosed = inspection.checks and inspection.checks.enclosed or nil
    local doorsFitted = inspection.checks and inspection.checks.doors_fitted or nil
    local doorsClosed = inspection.checks and inspection.checks.doors_closed or nil
    local goodBed = inspection.checks and inspection.checks.good_bed or nil
    local generator = inspection.checks and inspection.checks.generator or nil
    local food = inspection.checks and inspection.checks.food or nil
    local plumbedSink = inspection.checks and inspection.checks.plumbed_sink or nil
    local spareCar = inspection.checks and inspection.checks.spare_car or nil
    local previousStart = Store.getDeliverable(outpost.id, "engine_start")
    local started = previousStart and previousStart.passed == true or false
    if started then
        local latchedVehicleId = previousStart.details and previousStart.details.vehicleId or nil
        local latchedVehicle = latchedVehicleId and VehicleCheck.findBySqlId(latchedVehicleId) or nil
        if latchedVehicle and VehicleCheck.inSupportArea(outpost, latchedVehicle)
                and VehicleCheck.hasRequiredLatchState(latchedVehicle) then
            local facts = VehicleCheck.inspect(latchedVehicle)
            spareCar = {
                available = true,
                passed = true,
                current = 0,
                required = 0,
                state = "latched",
                fingerprint = "latched:" .. tostring(latchedVehicleId),
                details = { candidateCount = 1, vehicle = facts, failures = {},
                    latchedVehicleId = tostring(latchedVehicleId) },
            }
        elseif latchedVehicle or (getTimestampMs() >= canValidateMissingLatchedVehicleAt
                and VehicleCheck.supportAreaFullyLoaded(outpost)) then
            started = false
            previousStart = nil
        else
            -- World streaming has not yet proved that the latched car has left.
            -- Preserve the dependent spare-car result during that grace period so
            -- an export can never claim that the car was started but is absent.
            spareCar = {
                available = true,
                passed = true,
                current = 0,
                required = 0,
                state = "latched",
                fingerprint = "latched:" .. tostring(latchedVehicleId),
                details = previousStart.details,
            }
        end
    end
    local zombies = countZombies(outpost)
    local activationAvailable = activation and activation.error == nil
        and activation.activatedRooms ~= nil and activation.totalRooms ~= nil
    if activationAvailable then
        updateDeliverable(outpost, "room_activation", {
            passed = activation.passed,
            current = activation.activatedRooms,
            required = activation.totalRooms,
        })
        updateDeliverable(outpost, "floor_activation", {
            passed = activation.passed,
            current = activation.activatedFloors,
            required = activation.totalFloors,
        })
    end

    if zombies ~= nil then
        local previous = Store.getDeliverable(outpost.id, "zombie_clearance")
        local certified = activationAvailable and activation.passed == true and zombies == 0
            and getTimestampMs() >= canCertifyAt
        local cleared = certified or (previous and previous.passed == true)
        updateDeliverable(outpost, "zombie_clearance", {
            passed = cleared,
            current = cleared and 1 or 0,
            required = 1,
            state = cleared and "cleared" or "unclear",
        })
    end

    if windows and windows.available == true then
        updateDeliverable(outpost, "window_barricades", windows)
    end
    if enclosed and enclosed.available == true then
        updateDeliverable(outpost, "enclosed", enclosed)
    end
    if doorsFitted and doorsFitted.available == true then
        updateDeliverable(outpost, "doors_fitted", doorsFitted)
    end
    if doorsClosed and doorsClosed.available == true then
        updateDeliverable(outpost, "doors_closed", doorsClosed)
    end
    if goodBed and goodBed.available == true then
        updateDeliverable(outpost, "good_bed", goodBed)
    end
    if generator and generator.available == true then
        updateDeliverable(outpost, "generator", generator)
    end
    if food and food.available == true then
        updateDeliverable(outpost, "food", food)
    end
    if plumbedSink and plumbedSink.available == true then
        updateDeliverable(outpost, "plumbed_sink", plumbedSink)
    end
    if spareCar and spareCar.available == true then
        updateDeliverable(outpost, "spare_car", spareCar)
    end
    local engineStartAvailable = started or (spareCar and spareCar.passed == true)
    updateDeliverable(outpost, "engine_start", {
        available = engineStartAvailable,
        passed = started,
        current = started and 1 or 0,
        required = 1,
        state = started and "started" or "not_started",
        fingerprint = started and previousStart and previousStart.fingerprint or nil,
        details = started and previousStart and previousStart.details or nil,
    }, true)
    local record = Store.get(outpost.id)
    local completion = Completion.calculate(record)
    local completionTransition = Store.observeCompletion(
        outpost.id, completion.complete)
    if completionTransition == "completed" then
        ChallengeEvents.emit("outpost.completed", { outpostId = outpost.id, record = record })
    elseif completionTransition == "regressed" then
        ChallengeEvents.emit("outpost.regressed", { outpostId = outpost.id, record = record })
    end
    local progressAvailability = {
        room_activation = activationAvailable,
        floor_activation = activationAvailable,
        window_barricades = windows and windows.available == true,
        enclosed = enclosed and enclosed.available == true,
        doors_fitted = doorsFitted and doorsFitted.available == true,
        doors_closed = doorsClosed and doorsClosed.available == true,
        good_bed = goodBed and goodBed.available == true,
        generator = generator and generator.available == true,
        food = food and food.available == true,
        plumbed_sink = plumbedSink and plumbedSink.available == true,
        spare_car = spareCar and spareCar.available == true,
        engine_start = engineStartAvailable,
    }
    local allAuthoritative = true
    for _, available in pairs(progressAvailability) do
        if available ~= true then allAuthoritative = false; break end
    end
    local stageWasSealed = record.progressStage and record.progressStage.baselineSealed == true
    local baselineChanged = Store.updateProgressStage(outpost.id, completion.fractions, progressAvailability,
        allAuthoritative and getTimestampMs() >= canSealBaselineAt)
    if not stageWasSealed and baselineChanged then
        canSealBaselineAt = getTimestampMs() + BASELINE_SETTLE_MS
    end
    return record
end

function Runtime.getRecord(id)
    return Store.get(id)
end

function Runtime.getStatus(id)
    local record = Store.get(id)
    if not record.discovered then return "undiscovered" end
    if Completion.calculate(record).complete then return "complete" end
    if record.progressStage and record.progressStage.workStarted == true then return "in_progress" end
    return "discovered"
end

updateDeliverable = function(outpost, deliverableId, result, allowUnavailable)
    if not result or (result.available == false and allowUnavailable ~= true) then return false end
    local changed, current, previous = Store.updateDeliverable(outpost.id, deliverableId, result)
    if not changed then return false end
    Notifications.emit(outpost.id, deliverableId)
    ChallengeEvents.emit("outpost.deliverable.changed", {
        outpostId = outpost.id, deliverableId = deliverableId,
        previous = previous, current = current,
    })
    if previous and previous.passed ~= true and current and current.passed == true then
        ChallengeEvents.emit("outpost.deliverable.completed", {
            outpostId = outpost.id, deliverableId = deliverableId,
            previous = previous, current = current,
        })
    elseif previous and previous.passed == true
            and current and current.passed ~= true then
        ChallengeEvents.emit("outpost.deliverable.regressed", {
            outpostId = outpost.id, deliverableId = deliverableId,
            previous = previous, current = current,
        })
    end
    return true
end

local function updateActiveOutpost(player)
    local outpost = player and Outposts.getAtClearance(player:getX(), player:getY()) or nil
    if outpost ~= activeOutpost then
        activeOutpost = outpost
        lastRoom = nil
        evaluationPending = outpost ~= nil
        local now = getTimestampMs()
        nextFallbackAt = now + FALLBACK_INTERVAL_MS
        canCertifyAt = now + CERTIFICATION_GRACE_MS
        canSealBaselineAt = now + BASELINE_SETTLE_MS
        canValidateMissingLatchedVehicleAt = now + VEHICLE_LATCH_STREAM_GRACE_MS
        if outpost then
            markDiscovered(outpost)
        end
    end
    return outpost
end

local function onPlayerUpdate(player)
    if not ChallengeContext.isActive() then return end
    if player ~= (getSpecificPlayer(0) or getPlayer()) then return end
    local playerX = math.floor(player:getX())
    local playerY = math.floor(player:getY())
    if playerX ~= lastPlayerX or playerY ~= lastPlayerY then
        lastPlayerX = playerX
        lastPlayerY = playerY
        updateActiveOutpost(player)
    end
    local outpost = activeOutpost
    if not outpost then return end

    local vehicle = player:getVehicle()
    if vehicle then
        local vehicleId = tostring(vehicle:getSqlId())
        local running = vehicle:isEngineRunning() == true
        local starting = vehicle:isEngineStarted() == true
        local previouslyRunning = observedEngineStates[vehicleId]
        local previouslyStarting = observedStartingStates[vehicleId]
        observedEngineStates[vehicleId] = running
        observedStartingStates[vehicleId] = starting
        local spareCarRecord = Store.getDeliverable(outpost.id, "spare_car")
        if previouslyStarting ~= true and starting
                and spareCarRecord and spareCarRecord.passed == true
                and VehicleCheck.inSupportArea(outpost, vehicle)
                and VehicleCheck.qualifiesSuccessfulStart(vehicle) then
            armedEngineStarts[vehicleId] = outpost.id
        end
        if previouslyRunning == false and running
                and armedEngineStarts[vehicleId] == outpost.id
                and VehicleCheck.inSupportArea(outpost, vehicle)
                and VehicleCheck.qualifiesSuccessfulStart(vehicle) then
            local previousStart = Store.getDeliverable(outpost.id, "engine_start")
            if not previousStart or previousStart.passed ~= true then
                updateDeliverable(outpost, "engine_start", {
                    available = true,
                    passed = true,
                    current = 1,
                    required = 1,
                    state = "started",
                    fingerprint = vehicleId,
                    details = {
                        vehicleId = vehicleId,
                        scriptName = vehicle:getScriptName(),
                    },
                })
                evaluationPending = true
            end
            armedEngineStarts[vehicleId] = nil
        elseif not starting and not running then
            armedEngineStarts[vehicleId] = nil
        end
    end

    local square = player:getCurrentSquare()
    local room = square and square:getRoom() or nil
    if room ~= lastRoom then
        lastRoom = room
        evaluationPending = true
    end

    local now = getTimestampMs()
    if evaluationPending or now >= nextFallbackAt then
        evaluationPending = false
        nextFallbackAt = now + FALLBACK_INTERVAL_MS
        Runtime.evaluate(outpost, player)
    end
end

local function onZombieDead()
    if not ChallengeContext.isActive() then return end
    if activeOutpost then evaluationPending = true end
end

local function onGameStart()
    observedEngineStates = {}
    observedStartingStates = {}
    armedEngineStarts = {}
    activeOutpost = nil
    lastRoom = nil
    lastPlayerX = nil
    lastPlayerY = nil
    evaluationPending = false
    if not ChallengeContext.isActive() then return end
    local player = getSpecificPlayer(0) or getPlayer()
    if player then
        updateActiveOutpost(player)
        if activeOutpost then Runtime.evaluate(activeOutpost, player) end
    end
end

Events.OnPlayerUpdate.Add(onPlayerUpdate)
Events.OnZombieDead.Add(onZombieDead)
Events.OnGameStart.Add(onGameStart)

return Runtime
