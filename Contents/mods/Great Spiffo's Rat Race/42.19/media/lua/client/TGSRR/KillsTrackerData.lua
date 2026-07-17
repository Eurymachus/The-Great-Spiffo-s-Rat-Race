local Data = {}
local L = require "TGSRR/Localization"
local TARGET_KILLS = 1000000

Data.record = {
    id = "kills",
    label = L.text("UI_TGSRR_Tracker_ZombieKills", "Zombie Kills"),
    available = false,
    current = nil,
    target = TARGET_KILLS,
    percent = 0,
    status = "unavailable",
    detail = L.text("UI_TGSRR_Tracker_PlayerUnavailable", "Player data is unavailable."),
    detailTab = "kills",
}

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
    record.available = true
    record.current = current
    record.percent = math.max(0, math.min(100, current / TARGET_KILLS * 100))
    record.status = current >= TARGET_KILLS and "complete" or "in_progress"
    record.detail = L.text("UI_TGSRR_Tracker_KillsDetail", "Character Info zombie kill total.")
    return record
end

function Data.getRecord(player)
    if player and Data.record.current == nil then return Data.refresh(player) end
    return Data.record
end

local function onZombieDead()
    Data.refresh(getSpecificPlayer(0) or getPlayer())
end

Events.OnZombieDead.Add(onZombieDead)

return Data
