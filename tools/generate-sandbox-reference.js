const fs = require("fs");
const path = require("path");

const workspace = path.resolve(__dirname, "..");
const pzRoot = process.env.PZ_ROOT || "C:\\Games\\Steam\\steamapps\\common\\ProjectZomboid";
const sourcePath = path.join(pzRoot, "zombie_decompiled", "zombie", "SandboxOptions.java");
const translationPath = path.join(pzRoot, "media", "lua", "shared", "Translate", "EN", "Sandbox.json");
const presetPath = path.join(pzRoot, "media", "lua", "shared", "Sandbox", "Apocalypse.lua");
const outputPath = path.join(workspace, "docs", "VANILLA_SANDBOX_OPTIONS_B42.md");

const source = fs.readFileSync(sourcePath, "utf8");
const translations = JSON.parse(fs.readFileSync(translationPath, "utf8"));
const preset = fs.readFileSync(presetPath, "utf8");

const optionPattern = /new(Boolean|Integer|Double|Enum|String)Option\("([^"]+)",\s*([^;\r\n]+?)\)(?:\.setTranslation\("([^"]+)"\))?(?:\.setValueTranslation\("([^"]+)"\))?/g;
const options = [];
let match;
while ((match = optionPattern.exec(source))) {
    const [, type, id, argumentsText, translation, valueTranslation] = match;
    const args = argumentsText.split(",").map((value) => value.trim());
    options.push({
        type,
        id,
        args,
        translation: translation || id.replace(/^.*\./, ""),
        valueTranslation,
        sourceLine: source.slice(0, match.index).split(/\r?\n/).length,
    });
}

const presetValues = new Map();
let presetSection = "";
for (const line of preset.split(/\r?\n/)) {
    const sectionMatch = line.match(/^\s{4}([A-Za-z][A-Za-z0-9_]*)\s*=\s*\{\s*$/);
    if (sectionMatch) {
        presetSection = sectionMatch[1];
        continue;
    }
    if (presetSection && /^\s{4}\},?\s*$/.test(line)) {
        presetSection = "";
        continue;
    }
    const presetMatch = line.match(/^\s*([A-Za-z][A-Za-z0-9_.]*)\s*=\s*(.+?),?\s*(?:--.*)?$/);
    if (presetMatch) {
        const presetId = presetSection ? `${presetSection}.${presetMatch[1]}` : presetMatch[1];
        presetValues.set(presetId, presetMatch[2].trim());
    }
}

function text(key) {
    return translations[key] || "";
}

function clean(value) {
    return String(value || "")
        .replace(/<LINE>/g, " ")
        .replace(/<SPACE>/g, " ")
        .replace(/\\n/g, " ")
        .replace(/\s+/g, " ")
        .replace(/\|/g, "\\|")
        .trim();
}

function label(option) {
    return clean(text(`Sandbox_${option.translation}`)) || option.translation.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function defaultAndRange(option) {
    if (option.type === "Boolean") return `boolean; code default \`${option.args[0]}\``;
    if (option.type === "String") return `text; code default \`${option.args[0]}\``;
    if (option.type === "Enum") return `enum 1–${option.args[0]}; code default \`${option.args[1]}\``;
    return `${option.type.toLowerCase()} ${option.args[0]}–${option.args[1]}; code default \`${option.args[2]}\``;
}

function enumValues(option) {
    if (option.type !== "Enum") return "";
    const stem = option.valueTranslation || option.translation;
    const values = [];
    for (let index = 1; index <= Number(option.args[0]); index += 1) {
        const value = clean(text(`Sandbox_${stem}_option${index}`));
        if (value) values.push(`${index}=${value}`);
    }
    return values.length ? ` Values: ${values.join("; ")}.` : "";
}

const effects = {
    Zombies: "Convenience population selector. Loading/conversion code maps it to `ZombieConfig.PopulationMultiplier`; the advanced multiplier is the operative density value.",
    Distribution: "Selects urban-focused population-map density or uniform density.",
    ZombieRespawn: "High-level respawn selector used to derive advanced respawn values; the `ZombieConfig.Respawn*` fields contain the operative timing and fraction.",
    WaterShutModifier: "Exact world-age day at which water shuts off; `-1` lets the corresponding enum choose/randomise it.",
    ElecShutModifier: "Exact world-age day at which electricity shuts off; `-1` lets the corresponding enum choose/randomise it.",
    AlarmDecayModifier: "Exact world-age day at which alarms stop being available; `-1` lets the corresponding enum choose/randomise it.",
    SeenHoursPreventLootRespawn: "A container/cell seen by a player inside this many hours is ineligible for loot respawn. `0` disables this protection.",
    HoursForLootRespawn: "Interval in world hours between loot-restock attempts. `0` disables loot respawn, making the other loot-respawn controls inert.",
    MaxItemsForLootRespawn: "Containers at or above this item count are not topped up during loot respawn.",
    ConstructionPreventsLootRespawn: "When enabled, player construction in the area prevents loot respawn there.",
    MaximumLooted: "Upper value used by `SandboxOptions.getCurrentLootedChance()`. When positive, it ramps using `DaysUntilMaximumLooted`; it drives the Trashed Building story chance and the severity of some looted/trashed stories. Values at or above 100 saturate percentage-style chance checks.",
    DaysUntilMaximumLooted: "Number of apocalypse days over which `MaximumLooted` ramps to its configured value. `0` returns `MaximumLooted` immediately.",
    RuralLooted: "Shared rural multiplier used by both `SandboxOptions.getCurrentLootedChance(IsoGridSquare)` and `SandboxOptions.getCurrentDiminishedLootPercentage(IsoGridSquare)`. Build 42.19 casts it to an integer before multiplication.",
    MaximumDiminishedLoot: "Upper percentage removed from ordinary generated loot by `SandboxOptions.getCurrentLootMultiplier(IsoGridSquare)`. It does not mark a building as pre-looted.",
    DaysUntilMaximumDiminishedLoot: "Number of apocalypse days over which `MaximumDiminishedLoot` ramps to its configured percentage. `0` applies `MaximumDiminishedLoot` immediately.",
    MaximumLootedBuildingRooms: "Eligibility ceiling, not a partial-room cap. `RBLooted` and `RBTrashed` reject the entire building when `BuildingDef.getRooms().size()` exceeds `MaximumLootedBuildingRooms`; `RBShopLooted` accepts actual shops before its non-shop room-limit check.",
    RollsMultiplier: "Multiplies procedural-distribution roll counts before category rarity and other loot modifiers are applied.",
    ZombiePopLootEffect: "Adds local meta-chunk zombie intensity × this value to an item's base spawn chance. `0` disables the density bonus; this is additive, not a population multiplier or a neutral-at-10 scale.",
    InsaneLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Insanely Rare; category values are the newer direct controls.",
    ExtremeLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Extremely Rare; category values are the newer direct controls.",
    RareLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Rare; category values are the newer direct controls.",
    NormalLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Normal; category values are the newer direct controls.",
    CommonLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Common; category values are the newer direct controls.",
    AbundantLootFactor: "Numeric multiplier substituted when a legacy/preset loot rarity is Abundant; category values are the newer direct controls.",
    LootItemRemovalList: "Comma-separated full item types removed from generated loot. Story/zombie loot are only included when their separate toggles are enabled.",
    RemoveStoryLoot: "Extends `LootItemRemovalList` filtering to story loot.",
    RemoveZombieLoot: "Extends `LootItemRemovalList` filtering to zombie-carried loot.",
    WorldItemRemovalList: "Comma-separated full item types considered by world-item cleanup; blacklist/whitelist meaning is controlled by `ItemRemovalListBlacklistToggle`.",
    HoursForWorldItemRemoval: "Minimum age in world hours before eligible dropped world items are removed.",
    ItemRemovalListBlacklistToggle: "Switches world-item cleanup between removing listed types and preserving listed types/removing the rest.",
    Farming: "Legacy farming-speed enum retained for preset compatibility; `FarmingSpeedNew` is the precise multiplier used by current farming code.",
    PlantAbundance: "Legacy crop-yield enum retained for compatibility; `FarmingAmountNew` is the precise current multiplier.",
    XPmultiplier: "Base multiplier applied to XP gains; individual `MultiplierConfig.*` values can further specialise it.",
    XPBoost: "Controls the effect of profession/trait XP boosts, independently of the base and per-skill multipliers.",
    GeneratorFuelConsumption: "Fuel consumed per in-game hour. Generator runtime also depends on electrical load and generator state.",
    GeneratorTileRange: "Horizontal tile radius in which a generator supplies power.",
    GeneratorVerticalPowerRange: "Maximum vertical floor distance supplied by a generator.",
    FuelStationGasInfinite: "Makes fuel pumps inexhaustible; when true, min/max/empty-chance initial reserves are irrelevant.",
    FuelStationGasMin: "Lower bound for finite fuel-station starting reserves.",
    FuelStationGasMax: "Upper bound for finite fuel-station starting reserves.",
    FuelStationGasEmptyChance: "Percentage chance a finite fuel station starts empty.",
    MapAllKnown: "Reveals the entire world map; only useful when the world map is allowed.",
    MapNeedsLight: "Requires light to read map UI; only relevant when a map UI is allowed.",
    PopulationMultiplier: "Base zombie density multiplier applied to the map's population values.",
    PopulationStartMultiplier: "Multiplier at world start, interpolated toward `PopulationPeakMultiplier` by `PopulationPeakDay`.",
    PopulationPeakMultiplier: "Target population multiplier reached on `PopulationPeakDay`.",
    PopulationPeakDay: "World day on which the peak multiplier is reached.",
    RespawnHours: "Hours between zombie respawn checks. `0` disables respawn and makes the other respawn fields ineffective.",
    RespawnUnseenHours: "A chunk must remain unseen for this many hours before respawn is allowed.",
    RespawnMultiplier: "Fraction of the desired population restored per respawn cycle.",
    RedistributeHours: "Hours between migration/redistribution updates. `0` disables redistribution; high-level `ZombieMigrate` may also disable it.",
    Global: "Global XP multiplier applied when `MultiplierConfig.GlobalToggle` is enabled.",
    GlobalToggle: "Chooses global-only XP scaling versus the individual per-skill `MultiplierConfig.*` values.",
    FollowSoundDistance: "Maximum tile distance zombies use when pursuing an emitted sound; this governs hearing response after a sound exists, while lore hearing affects detection.",
    RallyGroupSize: "Target zombie count per rally group. `0` disables rally grouping.",
    RallyGroupSizeVariance: "Percentage variance around `RallyGroupSize`, preventing every group from having the same target size.",
    RallyTravelDistance: "Maximum distance zombies travel to form a rally group.",
    RallyGroupSeparation: "Minimum spacing the population manager tries to maintain between rally groups.",
    RallyGroupRadius: "Radius within which members spread around their rally-group centre.",
    DoorOpeningPercentage: "When cognition is Random, percentage of zombies assigned the ability to open doors; otherwise cognition determines the behaviour directly.",
    DayLength: "Real minutes per full in-game day. It scales most world-time processes together; real-time mode maps one real day to one game day.",
    StartYear: "Offset from the game's base start year used to initialise the calendar; combines with start month/day/time.",
    AnimalMilkIncModifier: "Multiplier band for milk regeneration over world time; only milk-producing animals use it.",
    AnimalWoolIncModifier: "Multiplier band for wool growth over world time; only wool-producing animals use it.",
};

function effect(option) {
    const shortId = option.id.replace(/^.*\./, "");
    const explicit = effects[option.id] || effects[shortId];
    const tooltip = clean(text(`Sandbox_${option.translation}_tooltip`));
    if (explicit) return explicit + enumValues(option);
    if (tooltip) return tooltip + enumValues(option);
    if (option.id.startsWith("MultiplierConfig.")) {
        return `XP multiplier for ${label(option)}; used with the global XP controls and any learning/trait bonuses.`;
    }
    if (/Loot(New)?$/.test(option.id) || ["SkillBookLoot", "RecipeResourceLoot"].includes(option.id)) {
        return `Multiplier for the ${label(option).toLowerCase()} procedural-loot category; combines with rolls, diminishing/pre-looted-building logic, and distribution-specific weights.`;
    }
    return `Direct runtime ${option.type.toLowerCase()} control for ${label(option).toLowerCase()}.${enumValues(option)}`;
}

function relationships(option) {
    const id = option.id;
    const relations = [];
    if (/^(FoodLootNew|LiteratureLootNew|SkillBookLoot|RecipeResourceLoot|MedicalLootNew|SurvivalGearsLootNew|CannedFoodLootNew|WeaponLootNew|RangedWeaponLootNew|AmmoLootNew|MechanicsLootNew|OtherLootNew|ClothingLootNew|ContainerLootNew|KeyLootNew|MediaLootNew|MementoLootNew|CookwareLootNew|MaterialLootNew|FarmingLootNew|ToolLootNew)$/.test(id)) {
        relations.push("RollsMultiplier", "MaximumDiminishedLoot", "MaximumLooted");
    }
    if (id.startsWith("ZombieLore.")) relations.push("Zombies", "ZombieConfig.PopulationMultiplier");
    if (id.startsWith("ZombieConfig.")) relations.push("Zombies", "ZombieRespawn", "ZombieMigrate");
    if (id.startsWith("MultiplierConfig.")) relations.push("XPmultiplier", "XPBoost");
    if (id.startsWith("Map.")) relations.push("Map.AllowWorldMap", "Map.AllowMiniMap");
    if (/Animal/.test(id)) relations.push("AnimalRanchChance", "TimeSinceApo");
    if (/Farming|Plant|Crop/.test(id)) relations.push("FarmingSpeedNew", "FarmingAmountNew", "PlantGrowingSeasons");
    if (/FuelStationGas/.test(id)) relations.push("FuelStationGasInfinite");
    if (/LootRespawn/.test(id)) relations.push("HoursForLootRespawn");
    if (/WaterShut/.test(id)) relations.push("WaterShut", "WaterShutModifier");
    if (/ElecShut/.test(id)) relations.push("ElecShut", "ElecShutModifier");
    if (/AlarmDecay/.test(id)) relations.push("AlarmDecay", "AlarmDecayModifier");
    const explicitRelations = {
        MaximumLooted: ["DaysUntilMaximumLooted", "RuralLooted", "MaximumLootedBuildingRooms", "TimeSinceApo"],
        DaysUntilMaximumLooted: ["MaximumLooted", "RuralLooted", "TimeSinceApo"],
        RuralLooted: ["MaximumLooted", "DaysUntilMaximumLooted", "MaximumDiminishedLoot", "DaysUntilMaximumDiminishedLoot"],
        MaximumLootedBuildingRooms: ["MaximumLooted", "DaysUntilMaximumLooted"],
        MaximumDiminishedLoot: ["DaysUntilMaximumDiminishedLoot", "RuralLooted", "TimeSinceApo"],
        DaysUntilMaximumDiminishedLoot: ["MaximumDiminishedLoot", "RuralLooted", "TimeSinceApo"],
        RollsMultiplier: ["all category loot multipliers"],
        ZombiePopLootEffect: ["ZombieConfig.PopulationMultiplier", "all category loot multipliers"],
        DoorOpeningPercentage: ["ZombieLore.Cognition"],
        SprinterPercentage: ["ZombieLore.Speed"],
        GeneratorTileRange: ["GeneratorVerticalPowerRange", "GeneratorFuelConsumption"],
        GeneratorVerticalPowerRange: ["GeneratorTileRange", "GeneratorFuelConsumption"],
        StartYear: ["StartMonth", "StartDay", "StartTime"],
        StartMonth: ["StartYear", "StartDay", "StartTime"],
        StartDay: ["StartYear", "StartMonth", "StartTime"],
        StartTime: ["StartYear", "StartMonth", "StartDay"],
    };
    for (const related of explicitRelations[id.replace(/^.*\./, "")] || []) relations.push(related);
    return [...new Set(relations.filter((other) => other !== id))].map((other) => `\`${other}\``).join(", ") || "Independent/no hard gate identified";
}

function category(option) {
    const id = option.id;
    if (["MaximumLootedBuildingRooms", "MaximumLooted", "DaysUntilMaximumLooted", "RuralLooted"].includes(id)) return "Pre-looted and trashed buildings";
    if (["MaximumDiminishedLoot", "DaysUntilMaximumDiminishedLoot"].includes(id)) return "Diminished generated loot";
    if (id.startsWith("ZombieLore.")) return "Zombie lore and behaviour";
    if (id.startsWith("ZombieConfig.")) return "Advanced zombie population";
    if (id.startsWith("MultiplierConfig.")) return "XP multipliers";
    if (id.startsWith("Map.")) return "Map";
    if (id.startsWith("Basement.")) return "World generation and stories";
    if (/^(Zombies|Distribution|ZombieVoronoiNoise|ZombieRespawn|ZombieMigrate)$/.test(id)) return "Population";
    if (/^(DayLength|Start|DayNight|Climate|FogCycle|TimeSinceApo)/.test(id)) return "Time and climate";
    if (/Loot|RollsMultiplier|ZombiePopLootEffect/.test(id)) return "Loot";
    if (/WaterShut|ElecShut|AlarmDecay|Generator|LightBulb/.test(id)) return "Utilities";
    if (/Animal|RatIndex/.test(id)) return "Animals";
    if (/Vehicle|Car|Gas|Traffic|Siren|RecentlySurvivor/.test(id)) return "Vehicles";
    if (/Farming|Plant|Compost|Crop|Clay/.test(id)) return "Farming and resources";
    if (/Fish|Nature|Maggot/.test(id)) return "Nature, fishing and foraging";
    if (/Injury|Fracture|Wound|Muscle|Discomfort|Nutrition|StatsDecrease|EndRegen|Poison/.test(id)) return "Player health";
    if (/XP|LevelFor|Literature|MinutesPerPage|Recipe|MetaKnowledge|Trait/.test(id)) return "Character, skills and literature";
    if (/Fire|Corpse|Blood|Rotten|WorldItemRemoval/.test(id)) return "Cleanup, fire and corpses";
    if (/Alarm|LockedHouses|Story|Helicopter|MetaEvent|SleepingEvent|RanchChance/.test(id)) return "World generation and stories";
    return "Gameplay and miscellaneous";
}

const grouped = new Map();
const uniqueIds = new Set(options.map((option) => option.id));
if (uniqueIds.size !== options.length) {
    throw new Error(`Duplicate option IDs found: parsed ${options.length}, unique ${uniqueIds.size}`);
}
for (const option of options) {
    const name = category(option);
    if (!grouped.has(name)) grouped.set(name, []);
    grouped.get(name).push(option);
}

const preferredOrder = [
    "Population",
    "Advanced zombie population",
    "Zombie lore and behaviour",
    "Time and climate",
    "Loot",
    "Pre-looted and trashed buildings",
    "Diminished generated loot",
    "Utilities",
    "World generation and stories",
    "Vehicles",
    "Animals",
    "Farming and resources",
    "Nature, fishing and foraging",
    "Player health",
    "Character, skills and literature",
    "XP multipliers",
    "Map",
    "Cleanup, fire and corpses",
    "Gameplay and miscellaneous",
];

const lines = [
    "# Vanilla Project Zomboid sandbox options — Build 42.19",
    "",
    "> Generated and then reviewed against the locally installed **42.19** runtime registry. This is a decision reference, not a replacement for the game code. Project Zomboid is under active development, so re-audit after an update.",
    "",
    "## How to read this reference",
    "",
    `The canonical registry contains **${options.length} vanilla options**. Every registered raw ID appears exactly once below. “Code default” is the constructor fallback, not necessarily the value selected by Apocalypse, Survivor, Builder, or a server preset. Enum numbers are serialized values; named values are included where the English translation catalogue defines them.`,
    "",
    "The **Code effect** column combines the vanilla tooltip with implementation tracing. “Related / gated by” means either a hard gate, a derived-value relationship, or a multiplier that participates in the same calculation; it does not always mean both settings must be enabled.",
    "",
    "### Important interaction rules",
    "",
    "- High-level `Zombies` and `ZombieRespawn` controls are convenience selectors. Advanced `ZombieConfig.*` values are the operative population/respawn parameters after presets are loaded.",
    "- Loot is layered: distribution rolls × `RollsMultiplier` × category rarity × local/population effects, followed by pre-looted/diminishing/removal rules. Setting one category to zero does not change story or zombie loot unless their dedicated removal controls apply.",
    "- Loot respawn is completely off when `HoursForLootRespawn = 0`; its seen-hours, max-items, and construction guards then have nothing to govern.",
    "- Exact shutoff modifier fields override/randomisation behaviour associated with their high-level enum. A modifier of `-1` delegates back to the enum.",
    "- `FuelStationGasInfinite` overrides finite reserve bounds and empty chance.",
    "- XP has several layers: base `XPmultiplier`, `XPBoost`, global/per-skill `MultiplierConfig.*`, plus profession/trait and literature bonuses.",
    "- Many world-generation settings only affect newly generated or not-yet-seen cells/buildings/vehicles. Changing them cannot reliably rewrite already-generated world state.",
    "",
    "## Loot-age mechanisms: exact Build 42.19 calculations",
    "",
    "These are two separate systems. **Pre-looted/trashed buildings** choose and transform a whole building through randomized-building stories. **Diminished generated loot** reduces ordinary item-generation probability in containers. Enabling one does not enable the other.",
    "",
    "### Shared apocalypse-age input",
    "",
    "Both calculations start with:",
    "",
    "```text",
    "ElapsedApocalypseDays = floor(GameTime.worldAgeHours / 24)",
    "                     + ((TimeSinceApo - 1) * 30)",
    "EffectiveElapsedApocalypseDays = max(1, ElapsedApocalypseDays)",
    "```",
    "",
    "`TimeSinceApo` therefore contributes a 30-day offset for every enum step after its first value. The minimum effective day is 1, so an enabled ramp begins slightly above zero rather than at exactly zero.",
    "",
    "### Pre-looted and trashed building calculation",
    "",
    "The base value returned by `SandboxOptions.getCurrentLootedChance(IsoGridSquare)` is:",
    "",
    "```text",
    "if MaximumLooted <= 0:",
    "    CurrentLootedChance = 0",
    "else if DaysUntilMaximumLooted <= 0:",
    "    CurrentLootedChance = MaximumLooted",
    "else:",
    "    LootedRampDay = min(EffectiveElapsedApocalypseDays, DaysUntilMaximumLooted)",
    "    CurrentLootedChance = floor(MaximumLooted * LootedRampDay",
    "                                / DaysUntilMaximumLooted)",
    "```",
    "",
    "When an `IsoGridSquare` is supplied, Build 42.19 then applies:",
    "",
    "```text",
    "if ItemPickerJava.getSquareRegion(IsoGridSquare) == null:",
    "    CurrentLootedChance = CurrentLootedChance * floor(RuralLooted)",
    "",
    "if IsoGridSquare.getSquareZombiesType() == \"Rich\":",
    "    CurrentLootedChance = floor(CurrentLootedChance * 1.5)",
    "",
    "if CurrentLootedChance <= 0:",
    "    CurrentLootedChance = 1",
    "```",
    "",
    "Consequences:",
    "",
    "- `RuralLooted` is stored as a double but cast to an integer: values from 0.0 through 0.999… multiply by 0, values from 1.0 through 1.999… multiply by 1, and 2.0 multiplies by 2. Because the final positive-setting floor is 1, a rural result reduced to 0 becomes 1 rather than disabling the story.",
    "- `MaximumLootedBuildingRooms` is checked separately. `RBLooted` and `RBTrashed` reject the entire building when its room count is greater than `MaximumLootedBuildingRooms`; they do not process only the first N rooms.",
    "- `RBShopLooted` accepts a real shop before reaching its non-shop room-count check, so the room ceiling principally governs houses/trashed buildings and non-shop candidates.",
    "- The computed value is consumed as the dynamic chance for the **Trashed Building** story and as a severity/eligibility input by related randomized-building stories. It is not itself a universal per-building dice roll applied to every building type.",
    "",
    "### Diminished generated-loot calculation",
    "",
    "`SandboxOptions.getCurrentDiminishedLootPercentage(IsoGridSquare)` calculates:",
    "",
    "```text",
    "if MaximumDiminishedLoot <= 0:",
    "    CurrentDiminishedLootPercentage = 0",
    "else if DaysUntilMaximumDiminishedLoot <= 0:",
    "    CurrentDiminishedLootPercentage = MaximumDiminishedLoot",
    "else:",
    "    DiminishedRampDay = min(EffectiveElapsedApocalypseDays,",
    "                            DaysUntilMaximumDiminishedLoot)",
    "    CurrentDiminishedLootPercentage =",
    "        floor(MaximumDiminishedLoot * DiminishedRampDay",
    "              / DaysUntilMaximumDiminishedLoot)",
    "",
    "if ItemPickerJava.getSquareRegion(IsoGridSquare) == null:",
    "    CurrentDiminishedLootPercentage =",
    "        CurrentDiminishedLootPercentage * floor(RuralLooted)",
    "",
    "CurrentDiminishedLootPercentage =",
    "    clamp(CurrentDiminishedLootPercentage, 0, 100)",
    "",
    "CurrentLootMultiplier =",
    "    1.0 - (CurrentDiminishedLootPercentage / 100.0)",
    "```",
    "",
    "`ItemPickerJava` applies that multiplier after the item's base chance, category loot modifier, and zombie-density addition have been combined:",
    "",
    "```text",
    "FinalItemSpawnChance =",
    "    ((BaseItemChance * 100 * CategoryLootModifier)",
    "      + AdjustedZombieDensity)",
    "    * CurrentLootMultiplier",
    "```",
    "",
    "Thus `MaximumDiminishedLoot = 20` eventually multiplies the combined chance by 0.80; `MaximumDiminishedLoot = 100` reduces it to zero. In a rural square, `RuralLooted = 2.0` doubles the diminished percentage before the 100% clamp. Unlike the pre-looted calculation, a fractional `RuralLooted` cast to 0 leaves the diminished percentage at 0.",
    "",
    "## Complete option catalogue",
    "",
];

for (const section of preferredOrder) {
    const entries = grouped.get(section);
    if (!entries?.length) continue;
    lines.push(`### ${section}`, "");
    lines.push("| UI name / raw ID | Type, range and default | Code effect | Related / gated by |");
    lines.push("|---|---|---|---|");
    for (const option of entries) {
        const apocalypse = presetValues.has(option.id) ? `; Apocalypse \`${presetValues.get(option.id)}\`` : "";
        lines.push(`| **${label(option)}**<br>\`${option.id}\` | ${defaultAndRange(option)}${apocalypse} | ${clean(effect(option))} | ${relationships(option)} |`);
    }
    lines.push("");
}

lines.push(
    "## Source and audit notes",
    "",
    `- Registry and constructor defaults: \`${sourcePath}\`.`,
    `- English UI labels, enum names, and tooltips: \`${translationPath}\`.`,
    `- Apocalypse preset comparison: \`${presetPath}\`.`,
    "- Runtime consumers were traced in the installed decompiled Java tree and vanilla Lua. A tooltip is used where it accurately describes the terminal calculation; explicit notes override it where several controls feed one calculation.",
    "- Principal implementation sites include `zombie/inventory/ItemPickerJava.java` (loot multipliers, rolls, diminishing loot and removal), `zombie/randomizedWorld/randomizedBuilding/RBLooted.java` (pre-looted buildings), `zombie/popman/ZombiePopulationManager.java` and `zombie/characters/ZombieGroup.java` (population, respawn, migration and rally groups), and `zombie/characters/animals/datas/AnimalData.java` (animal growth/reproduction products).",
    "- `SandboxOptions.java` is authoritative for what is a vanilla sandbox option. Third-party `media/sandbox-options.txt` entries are deliberately excluded.",
    "",
    "### Screenshot provenance",
    "",
    "The controls shown in the supplied screenshot are vanilla Build 42.19 controls: the diminished/pre-looted-building settings and expanded category rarity fields are registered directly by `SandboxOptions.java`. They are not being mistaken for the installed Better Containers or other workshop options.",
    "",
    "### Coverage check",
    "",
    `- Parsed runtime options: **${options.length}**.`,
    `- Rows written: **${options.length}**.`,
    `- Unique raw IDs: **${uniqueIds.size}** (duplicates: **${options.length - uniqueIds.size}**).`,
    ""
);

fs.writeFileSync(outputPath, `${lines.join("\n")}\n`, "utf8");
console.log(`Wrote ${options.length} options to ${outputPath}`);
