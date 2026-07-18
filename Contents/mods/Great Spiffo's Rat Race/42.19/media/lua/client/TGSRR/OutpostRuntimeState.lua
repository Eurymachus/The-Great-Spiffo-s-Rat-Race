local Outposts = require "TGSRR/OutpostDefinitions"
local Store = require "TGSRR/OutpostProgressStore"
local Notifications = require "TGSRR/DeliverableNotifications"
local Completion = require "TGSRR/OutpostCompletion"
local ChallengeEvents = require "TGSRR/ChallengeEvents"
require "TGSRR/ChallengeMilestones"
require "TGSRR/OutpostRoomActivationCheck"
require "TGSRR/OutpostGroundFloorWindowCheck"
require "TGSRR/OutpostEnclosureChecks"
require "TGSRR/OutpostFixtureChecks"
require "TGSRR/OutpostVehicleCheck"

local Runtime = {}
local FALLBACK_INTERVAL_MS = 1000
local CERTIFICATION_GRACE_MS = 10000
local BASELINE_SETTLE_MS = 10000

local activeOutpost = nil
local lastRoom = nil
local lastPlayerX = nil
local lastPlayerY = nil
local nextFallbackAt = 0
local canCertifyAt = 0
local canSealBaselineAt = 0
local evaluationPending = false

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
    if not outpost or not player then return nil end
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
        updateDeliverable(outpost, "zombie_clearance", {
            passed = certified or (previous and previous.passed == true),
            current = zombies,
            required = 0,
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
    local record = Store.get(outpost.id)
    local completion = Completion.calculate(record)
    if Store.observeCompletion(outpost.id, completion.complete) then
        ChallengeEvents.emit("outpost.completed", { outpostId = outpost.id, record = record })
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

local function updateDeliverable(outpost, deliverableId, result)
    if not result or result.available == false then return false end
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
        if outpost then
            markDiscovered(outpost)
        end
    end
    return outpost
end

local function onPlayerUpdate(player)
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
    if activeOutpost then evaluationPending = true end
end

local function onGameStart()
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
