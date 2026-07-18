local Completion = {}

local WEIGHTS = {
    discovery = 2,
    room_activation = 8,
    floor_activation = 4,
    zombie_clearance = 15,
    window_barricades = 10,
    enclosed = 10,
    doors_fitted = 5,
    doors_closed = 3,
    good_bed = 6,
    generator = 8,
    food = 8,
    plumbed_sink = 8,
    spare_car = 13,
}

local REQUIRED = {
    "room_activation", "floor_activation", "zombie_clearance",
    "window_barricades", "enclosed", "doors_fitted", "doors_closed",
    "good_bed", "generator", "food", "plumbed_sink", "spare_car",
}

local function clamp(value)
    return math.max(0, math.min(1, tonumber(value) or 0))
end

local function ratio(deliverable)
    if not deliverable then return 0 end
    local required = tonumber(deliverable.required) or 0
    if required <= 0 then return deliverable.passed and 1 or 0 end
    return clamp((tonumber(deliverable.current) or 0) / required)
end

local function generatorRatio(deliverable)
    if not deliverable or deliverable.state ~= "fuel" then return 0 end
    return ratio(deliverable)
end

local function spareCarRatio(deliverable)
    if not deliverable then return 0 end
    if deliverable.passed then return 1 end
    local details = deliverable.details
    local vehicle = details and details.vehicle or nil
    local tyres = vehicle and vehicle.tyres or nil
    if type(tyres) ~= "table" then return 0 end
    local total = 5 + #tyres * 2
    if #tyres == 0 then total = total + 1 end
    local failures = math.max(0, tonumber(deliverable.current) or total)
    return clamp((total - failures) / total)
end

function Completion.getWeights()
    return WEIGHTS
end

function Completion.calculate(record)
    record = record or {}
    local deliverables = record.deliverables or {}
    local fractions = {
        discovery = record.discovered == true and 1 or 0,
        room_activation = ratio(deliverables.room_activation),
        floor_activation = ratio(deliverables.floor_activation),
        zombie_clearance = deliverables.zombie_clearance and deliverables.zombie_clearance.passed and 1 or 0,
        window_barricades = ratio(deliverables.window_barricades),
        enclosed = ratio(deliverables.enclosed),
        doors_fitted = ratio(deliverables.doors_fitted),
        doors_closed = ratio(deliverables.doors_closed),
        good_bed = deliverables.good_bed and deliverables.good_bed.passed and 1 or 0,
        generator = generatorRatio(deliverables.generator),
        food = ratio(deliverables.food),
        plumbed_sink = deliverables.plumbed_sink and deliverables.plumbed_sink.passed and 1 or 0,
        spare_car = spareCarRatio(deliverables.spare_car),
    }

    local percent = 0
    for id, weight in pairs(WEIGHTS) do percent = percent + weight * (fractions[id] or 0) end

    local passedRequirements = record.discovered == true and 1 or 0
    for _, id in ipairs(REQUIRED) do
        local deliverable = deliverables[id]
        if deliverable and deliverable.passed == true then
            passedRequirements = passedRequirements + 1
        end
    end

    local totalRequirements = #REQUIRED + 1
    local complete = record.discovered == true
    if complete then
        for _, id in ipairs(REQUIRED) do
            local deliverable = deliverables[id]
            if not deliverable or deliverable.passed ~= true then
                complete = false
                break
            end
        end
    end

    return {
        complete = complete,
        progress = clamp(percent / 100),
        percent = math.max(0, math.min(100, percent)),
        fractions = fractions,
        passedRequirements = passedRequirements,
        totalRequirements = totalRequirements,
    }
end

return Completion
