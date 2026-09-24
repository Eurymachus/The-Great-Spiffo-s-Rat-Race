local GeneratorKnowledgeSnapshot = {}

function GeneratorKnowledgeSnapshot.observe(run)
    local state = type(run) == "table"
        and type(run.generatorKnowledge) == "table"
        and run.generatorKnowledge or {}
    local evidence = type(state.evidence) == "table" and state.evidence or {}
    return {
        schema = 1,
        recipeId = "Generator",
        known = state.known == true,
        knownAtTrackingStart = state.knownAtTrackingStart == true,
        partial = state.partial == true,
        firstObservedUtc = math.max(0,
            math.floor(tonumber(state.firstObservedUtc) or 0)),
        firstObservedWorldAgeHours = math.max(0,
            tonumber(state.firstObservedWorldAgeHours) or 0),
        survivedDays = math.max(0, tonumber(state.survivedDays) or 0),
        evidence = {
            professionId = tostring(evidence.professionId or ""),
            electricalLevel = math.max(0,
                math.floor(tonumber(evidence.electricalLevel) or 0)),
            inventive = evidence.inventive == true,
            generatorMagazineCompleted =
                evidence.generatorMagazineCompleted == true,
        },
    }
end

return GeneratorKnowledgeSnapshot
