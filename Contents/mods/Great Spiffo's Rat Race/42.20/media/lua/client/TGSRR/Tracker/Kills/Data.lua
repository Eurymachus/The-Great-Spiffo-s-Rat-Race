local Data = {}
local L = require "TGSRR/Core/Localization"
local ChallengeEvents = require "TGSRR/Core/Events"
local Milestones = require "TGSRR/Milestones/Definitions"
local TARGET_KILLS = 1000000

Data.record = {
    id = "kills",
    label = L.text("UI_TGSRR_Tracker_ZombieKills", "Kills"),
    available = false,
    current = nil,
    target = TARGET_KILLS,
    percent = 0,
    status = "unavailable",
    detail = L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable."),
    detailTab = "kills",
}

local lastObserved = nil

local function characterId(player)
    local username = player and player.getUsername and player:getUsername() or nil
    if username and username ~= "" then return username end
    local descriptor = player and player:getDescriptor() or nil
    local forename = descriptor and descriptor:getForename() or "player"
    local surname = descriptor and descriptor:getSurname() or ""
    return tostring(forename) .. ":" .. tostring(surname)
end

local function emitCrossedMilestones(player, current)
    if lastObserved == nil or current < lastObserved then
        lastObserved = current
        return
    end
    if current > lastObserved then
        for _, threshold in ipairs(Milestones.killThresholds) do
            if lastObserved < threshold and current >= threshold then
                ChallengeEvents.emit("kills.milestone.reached", {
                    threshold = threshold,
                    previous = lastObserved,
                    current = current,
                    characterId = characterId(player),
                })
            end
        end
    end
    lastObserved = current
end

function Data.refresh(player)
    local record = Data.record
    if not player then
        record.available = false
        record.current = nil
        record.percent = 0
        record.status = "unavailable"
        record.detail = L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable.")
        return record
    end

    local current = math.max(0, player:getZombieKills())
    emitCrossedMilestones(player, current)
    record.available = true
    record.current = current
    record.percent = math.max(0, math.min(100, current / TARGET_KILLS * 100))
    record.status = current >= TARGET_KILLS and "complete" or "in_progress"
    record.detail = L.text("UI_TGSRR_Tracker_KillsDetail", "Character Info zombie kill total.")
    return record
end

function Data.getMilestones() return Milestones.killThresholds end

function Data.getRecord(player)
    if player and Data.record.current == nil then return Data.refresh(player) end
    return Data.record
end

local function onZombieDead()
    Data.refresh(getSpecificPlayer(0) or getPlayer())
end

Events.OnZombieDead.Add(onZombieDead)

return Data
