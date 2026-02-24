local Challenge = {}

local TGSRR_SandboxBase = require("LastStand/TGSRR_SandboxBase")

Challenge.id = "TGSRR_CDDA";
Challenge.completionText = "Survive a night to unlock next challenge.";
Challenge.image = "media/lua/client/LastStand/outpostmap.png";
Challenge.video = "CDDA.bik";
Challenge.gameMode = "The Great Spiffo's Rat Race - CDDA";
Challenge.world = "DEFAULT";
Challenge.hourOfDay = 7;

Challenge.Add = function()
	addChallenge(Challenge);
end

Challenge.getSpawnRegion = function()
	return SpawnRegionMgr.getSpawnRegions();
end

Challenge.OnInitWorld = function()
	TGSRR_SandboxBase.apply()

	-- challenge delta
	SandboxVars.TimeSinceApo = 13;

	Events.OnGameStart.Add(Challenge.OnGameStart);
end

Challenge.OnGameStart = function()
	local pl = getPlayer();

	if pl:getHoursSurvived() > 0 then return end

	local square = pl:getCurrentSquare();
	if not square then return end
	local room = square:getRoom();
	if not room then return end
	local building = room:getBuilding();
	if not building then return end

	local i = 0
	while i <= 4 do
		local tile = building:getRandomRoom():getRandomSquare();
		if tile:getRoom() == room then
			-- nothing
		else
			i = i + 1;
	        IsoFireManager.explode(getCell(), tile, 100000)
		end
	end
end

Challenge.AddPlayer = function(playerNum, playerObj)
	if playerObj:getHoursSurvived() > 0 then return end

	playerObj:getStats():set(CharacterStat.INTOXICATION, 100);

	playerObj:getInventory():clear();
	playerObj:clearWornItems();
	playerObj:getStats():set(CharacterStat.WETNESS, CharacterStat.WETNESS:getMaximumValue());
	playerObj:getBodyDamage():setCatchACold(0.0);
	playerObj:getBodyDamage():setHasACold(true);
	playerObj:getBodyDamage():setColdStrength(20.0);
	playerObj:getBodyDamage():setTimeToSneezeOrCough(0);
	playerObj:setClothingItem_Feet(nil)
	playerObj:setClothingItem_Legs(nil)
	playerObj:setClothingItem_Torso(nil)
	playerObj:getBodyDamage():getBodyPart(BodyPartType.Groin):generateDeepShardWound();
end

Challenge.RemovePlayer = function(p)

end

Challenge.Render = function()
    --~ 	getTextManager():DrawStringRight(UIFont.Small, getCore():getOffscreenWidth() - 20, 20, "Zombies left : " .. (EightMonthsLater.zombiesSpawned - EightMonthsLater.deadZombie), 1, 1, 1, 0.8);
    --~ 	getTextManager():DrawStringRight(UIFont.Small, (getCore():getOffscreenWidth()*0.9), 40, "Next wave : " .. tonumber(((60*60) - EightMonthsLater.waveTime)), 1, 1, 1, 0.8);
end

Events.OnChallengeQuery.Add(Challenge.Add)

