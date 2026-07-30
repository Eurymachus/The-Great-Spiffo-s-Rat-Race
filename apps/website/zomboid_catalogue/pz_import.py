import json
import re
from dataclasses import dataclass, field
from pathlib import Path


BLOCK_PATTERN = re.compile(
    r"(?P<type>character_trait_definition|character_profession_definition)"
    r"\s+(?P<id>[^\s{]+)\s*\{(?P<body>.*?)^\s*\}",
    re.MULTILINE | re.DOTALL,
)
FIELD_PATTERN = re.compile(r"^\s*(?P<key>\w+)\s*=\s*(?P<value>.*?),\s*$", re.MULTILINE)
SKILL_PATTERN = re.compile(
    r"(?:PerkFactory\.)?AddPerk\(\s*(?:PerkFactory\.)?Perks\.(?P<id>\w+),"
    r"\s*\"(?P<translation>[^\"]+)\""
    r"(?:,\s*(?:PerkFactory\.)?Perks\.(?P<parent>\w+))?,\s*"
    r"(?P<xp>\d+(?:,\s*\d+){9})(?:,\s*(?P<passive>true|false))?\s*\);"
)
ITEM_PATTERN = re.compile(
    r"^\s*item\s+(?P<id>[^\s{]+)\s*\{(?P<body>.*?)^\s*\}",
    re.MULTILINE | re.DOTALL,
)
MODULE_PATTERN = re.compile(r"^\s*module\s+(?P<id>[^\s{]+)", re.MULTILINE)

WEAPON_SKILLS = {
    "base:axe": "Axe",
    "base:longblade": "LongBlade",
    "base:smallblade": "SmallBlade",
    "base:smallblunt": "SmallBlunt",
    "base:blunt": "Blunt",
    "base:spear": "Spear",
}


@dataclass(frozen=True)
class ParsedDefinition:
    stable_id: str
    fields: dict[str, str]


@dataclass(frozen=True)
class ParsedSkill:
    stable_id: str
    translation_key: str
    parent_id: str
    level_xp: list[int]
    is_passive: bool


@dataclass(frozen=True)
class ParsedItem:
    stable_id: str
    fields: dict[str, str]

    @property
    def tags(self):
        return PZCatalogueSource.split_values(self.fields.get("Tags", ""))

    @property
    def weapon_categories(self):
        return PZCatalogueSource.split_values(self.fields.get("Categories", ""))

    @property
    def capabilities(self):
        item_type = self.fields.get("ItemType", "").lower()
        display_category = self.fields.get("DisplayCategory", "").lower()
        tags = {value.lower() for value in self.tags}
        capabilities = set()
        if item_type == "base:weapon":
            capabilities.add("weapon")
        if "tool" in display_category:
            capabilities.add("tool")
        if item_type == "base:literature":
            capabilities.add("literature")
        if "base:magazine" in tags:
            capabilities.add("magazine")
        if "book_subject" in self.fields or {"base:hardcover", "base:hollowbook"} & tags:
            capabilities.add("book")
        return sorted(capabilities)

    @property
    def weapon_skill(self):
        if self.fields.get("SubCategory", "").lower() == "firearm":
            return "Aiming"
        for category in self.weapon_categories:
            if category.lower() in WEAPON_SKILLS:
                return WEAPON_SKILLS[category.lower()]
        return ""


@dataclass
class PZCatalogueSource:
    root: Path
    decompiled_root: Path | None = None
    translations: dict[str, str] = field(init=False)

    def __post_init__(self):
        self.root = self.root.resolve()
        if self.decompiled_root is not None:
            self.decompiled_root = self.decompiled_root.resolve()
        required = (
            self.trait_definitions_path,
            self.occupation_definitions_path,
            self.ui_translation_path,
            self.ig_ui_translation_path,
            self.item_name_translation_path,
            self.perk_factory_path,
            self.generated_items_root,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ValueError("Required Project Zomboid sources are missing: " + ", ".join(missing))
        self.translations = {}
        for path in (
            self.ui_translation_path,
            self.ig_ui_translation_path,
            self.item_name_translation_path,
        ):
            self.translations.update(
                json.loads(path.read_text(encoding="utf-8-sig"))
            )

    @property
    def trait_definitions_path(self):
        return self.root / "media/scripts/generated/characters/character_traits.txt"

    @property
    def occupation_definitions_path(self):
        return self.root / "media/scripts/generated/characters/character_professions.txt"

    @property
    def ui_translation_path(self):
        return self.root / "media/lua/shared/Translate/EN/UI.json"

    @property
    def ig_ui_translation_path(self):
        return self.root / "media/lua/shared/Translate/EN/IG_UI.json"

    @property
    def item_name_translation_path(self):
        return self.root / "media/lua/shared/Translate/EN/ItemName.json"

    @property
    def generated_items_root(self):
        return self.root / "media/scripts/generated/items"

    @property
    def perk_factory_path(self):
        root = self.decompiled_root or self.root / "zombie_decompiled"
        return root / "zombie/characters/skills/PerkFactory.java"

    @property
    def loose_trait_icon_root(self):
        return self.root / "media/ui/Traits"

    def traits(self):
        return self._definitions(self.trait_definitions_path, "character_trait_definition")

    def occupations(self):
        return self._definitions(
            self.occupation_definitions_path, "character_profession_definition"
        )

    def skills(self):
        text = self.perk_factory_path.read_text(encoding="utf-8")
        for match in SKILL_PATTERN.finditer(text):
            yield ParsedSkill(
                stable_id=match.group("id"),
                translation_key=match.group("translation"),
                parent_id=match.group("parent") or "",
                level_xp=[int(value.strip()) for value in match.group("xp").split(",")],
                is_passive=match.group("passive") == "true",
            )

    def items(self):
        definitions = {}
        for path in sorted(self.generated_items_root.glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            module_match = MODULE_PATTERN.search(text)
            module = module_match.group("id") if module_match else "Base"
            for match in ITEM_PATTERN.finditer(text):
                item = ParsedItem(
                    stable_id=f"{module}.{match.group('id')}",
                    fields={
                        field.group("key"): field.group("value").strip()
                        for field in FIELD_PATTERN.finditer(match.group("body"))
                    },
                )
                # Generated scripts can redefine an item in a later file. Match
                # the game's effective definition by retaining the final one.
                definitions[item.stable_id] = item
        yield from definitions.values()

    def item_name(self, stable_id):
        return self.display_text(stable_id, stable_id)

    def item_display_category_name(self, stable_id):
        return self.display_text(f"IGUI_ItemCat_{stable_id}", stable_id)

    def display_text(self, key, fallback=""):
        return self.translations.get(key, fallback)

    def skill_name(self, translation_key):
        return self.display_text(f"IGUI_perks_{translation_key}", translation_key)

    def skill_description(self, translation_key):
        description = self.display_text(f"IGUI_perks_{translation_key}_Description")
        if description:
            return description
        display_key = re.sub(r"[^A-Za-z0-9]", "", self.skill_name(translation_key))
        return self.display_text(f"IGUI_perks_{display_key}_Description")

    def trait_icon(self, stable_id):
        suffix = stable_id.split(":", 1)[-1].replace(" ", "_")
        candidates = (
            self.loose_trait_icon_root / f"trait_{suffix}.png",
            self.loose_trait_icon_root / f"trait_{suffix.lower()}.png",
        )
        return next((path for path in candidates if path.is_file()), None)

    @staticmethod
    def split_values(value):
        return [item for item in (part.strip() for part in value.split(";")) if item]

    @classmethod
    def xp_boosts(cls, value):
        boosts = {}
        for item in cls.split_values(value):
            key, amount = item.rsplit("=", 1)
            boosts[key] = int(amount)
        return boosts

    @staticmethod
    def truthy(value):
        return value.strip().lower() == "true"

    @staticmethod
    def _definitions(path, expected_type):
        text = path.read_text(encoding="utf-8")
        for match in BLOCK_PATTERN.finditer(text):
            if match.group("type") != expected_type:
                continue
            fields = {
                field.group("key"): field.group("value").strip()
                for field in FIELD_PATTERN.finditer(match.group("body"))
            }
            yield ParsedDefinition(match.group("id"), fields)
