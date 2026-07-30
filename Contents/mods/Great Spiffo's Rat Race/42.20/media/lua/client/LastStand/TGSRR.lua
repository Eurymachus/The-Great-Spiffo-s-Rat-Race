local Challenge = {}

local TGSRR_SandboxBase = require("TGSRR/Sandbox/Base")
local TGSRR_SelectedChallenge = require("TGSRR/Run/SelectedChallenge")
local TGSRR_CHALLENGE_IDS = {
    TGSRR = true,
    TGSRR_SevenMonths = true,
}

Challenge.id = "TGSRR";
Challenge.completionText = "Survive a night to unlock next challenge.";
Challenge.image = "media/lua/client/LastStand/outpostmap.png";
Challenge.gameMode = "The Great Spiffo's Rat Race";
Challenge.world = "DEFAULT";
TGSRR_SelectedChallenge.register(Challenge)

Challenge.Add = function()
	addChallenge(Challenge);
end

--[[
Challenge.getSpawnRegion = function()
	return SpawnRegionMgr.getSpawnRegions();
end
]]

Challenge.getSpawnRegion = function()
    local regions = {}

    for _, dir in ipairs(getMapDirectoryTable()) do
        local file = "media/maps/" .. dir .. "/spawnpoints.lua"

        if fileExists(file) then
            table.insert(regions, {
                name = dir,
                file = file
            })
        end
    end

    return SpawnRegionMgr.loadSpawnRegions(regions)
end

local function TGSRR_shouldShowMapSpawnInfo(info)
    if not info.only_for_game_mode then
        return true
    end

    local currentMode = GameMode.get(ResourceLocation.of(getCore():getGameMode()))
    if currentMode == info.only_for_game_mode then
        return true
    end

    if not getCore():isChallenge() then
        return false
    end

    if not TGSRR_CHALLENGE_IDS[getCore():getChallengeID()] then
        return false
    end

    local sandboxMode = GameMode.get(ResourceLocation.of("Sandbox"))
    return sandboxMode == info.only_for_game_mode
end

function MapSpawnSelect:fillList()
    self.listbox:clear()
    WORLD_MAP = nil
    self.mapPanel:clear()
    local spawnSelectImagePyramid = nil

    self.sortedList = {}
    self.notSortedList = {}

    local regions = self:getSpawnRegions()
    if not regions then return end

    for _, v in ipairs(regions) do
        local info = getMapInfo(v.name)
        if info then
            if TGSRR_shouldShowMapSpawnInfo(info) then
                local item = {}
                item.name = info.title or "NO TITLE"
                item.region = v
                item.dir = v.name
                item.desc = info.description or "NO DESCRIPTION"

                if info.spawnSelectImagePyramid then
                    spawnSelectImagePyramid = info.spawnSelectImagePyramid
                end

                item.zoomX = info.zoomX
                item.zoomY = info.zoomY
                item.zoomS = info.zoomS
                item.demoVideo = info.demoVideo

                self:checkSorted(item)
            end
        else
            local item = {}
            item.name = v.name
            item.region = v
            item.dir = ""
            item.desc = ""
            item.worldimage = nil

            self:checkSorted(item)
        end
    end

    if #self.listbox.items > 1 then
        local item = {}
        item.name = getText("UI_mapspawn_random")
        item.region = nil
        item.dir = ""
        item.desc = ""
        item.worldimage = nil

        table.insert(self.notSortedList, item)
    end

    if spawnSelectImagePyramid then
        self.mapPanel:setImagePyramid(spawnSelectImagePyramid)
    else
        for _, v in ipairs(regions) do
            local info = getMapInfo(v.name)
            if info then
                self.mapPanel:initMapData("media/maps/" .. v.name)

                for _, dir in ipairs(info.lots) do
                    self.mapPanel:initMapData("media/maps/" .. dir)
                end
            end
        end
    end

    for _, v in ipairs(self.sortedList) do
        self.listbox:addItem(v.name, v)
    end

    for _, v in ipairs(self.notSortedList) do
        self.listbox:addItem(v.name, v)
    end

    self:hideOrShowSaveName()
    self:recalculateMapSize()

    if self.textEntry ~= nil and self.textEntry:getInternalText() == "" then
        local sdf = SimpleDateFormat.new("yyyy-MM-dd_HH-mm-ss", Locale.ENGLISH)
        self.textEntry:setText(sdf:format(Calendar.getInstance():getTime()))
    end

    self.mapPanel.shownInitialLocation = false
end

Challenge.OnInitWorld = function()
	TGSRR_SandboxBase.apply()

	Events.OnGameStart.Add(Challenge.OnGameStart);
end

Challenge.OnGameStart = function()

end

Challenge.AddPlayer = function(playerNum, playerObj)

end

Challenge.RemovePlayer = function(p)

end

Challenge.Render = function()
    --~ 	getTextManager():DrawStringRight(UIFont.Small, getCore():getOffscreenWidth() - 20, 20, "Zombies left : " .. (EightMonthsLater.zombiesSpawned - EightMonthsLater.deadZombie), 1, 1, 1, 0.8);
    --~ 	getTextManager():DrawStringRight(UIFont.Small, (getCore():getOffscreenWidth()*0.9), 40, "Next wave : " .. tonumber(((60*60) - EightMonthsLater.waveTime)), 1, 1, 1, 0.8);
end

Events.OnChallengeQuery.Add(Challenge.Add)

