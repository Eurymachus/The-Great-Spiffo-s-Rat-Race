local Challenge = {}

local TGSRR_SandboxBase = require("LastStand/TGSRR_SandboxBase")

Challenge.id = "TGSRR";
Challenge.completionText = "Survive a night to unlock next challenge.";
Challenge.image = "media/lua/client/LastStand/outpostmap.png";
Challenge.gameMode = "The Great Spiffo's Rat Race";
Challenge.world = "DEFAULT";

Challenge.Add = function()
	addChallenge(Challenge);
end

Challenge.getSpawnRegion = function()
	return SpawnRegionMgr.getSpawnRegions();
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

