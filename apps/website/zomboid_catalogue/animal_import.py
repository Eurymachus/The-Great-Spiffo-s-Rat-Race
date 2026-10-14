"""Read literal animal metadata without executing game Lua."""
import re
from dataclasses import dataclass


ANIMAL_FIELD = re.compile(
    r'^\s*AnimalDefinitions\.animals\["([^"\n]+)"\]\.(\w+)\s*=\s*(.*?);?\s*$'
)
BREED_ICON = re.compile(
    r'^\s*AnimalDefinitions\.breeds\["([^"\n]+)"\]\.breeds\["([^"\n]+)"\]'
    r'\.(invIcon\w+)\s*=\s*"([^"\n]+)"\s*;?\s*$'
)
BREED_REFERENCE = re.compile(r'AnimalDefinitions\.breeds\["([^"\n]+)"\]\.breeds')


@dataclass(frozen=True)
class ParsedAnimal:
    stable_id: str
    species_id: str
    life_stage: str
    icon_key: str


def read_animals(root):
    if not root.is_dir():
        raise ValueError(f"Animal definition directory is missing: {root}")
    animals, breeds = {}, {}
    for path in sorted(root.glob("*Definitions.lua")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            # Only anchored literal assignments are read. Commented definitions
            # and unrelated functions cannot become catalogue records.
            line = line.split("--", 1)[0].strip()
            match = ANIMAL_FIELD.fullmatch(line)
            if match:
                identifier, key, value = match.groups()
                animals.setdefault(identifier, {})[key] = value.rstrip(";").strip()
            match = BREED_ICON.fullmatch(line)
            if match:
                species, breed, key, value = match.groups()
                breeds.setdefault(species, {}).setdefault(breed, {})[key] = value

    if not animals or not breeds:
        raise ValueError(f"No supported animal definitions found in {root}")
    babies = {fields["babyType"].strip('"') for fields in animals.values()
              if fields.get("babyType", "").startswith('"')}
    for identifier, fields in sorted(animals.items()):
        reference = BREED_REFERENCE.search(fields.get("breeds", ""))
        if not reference:
            continue
        species = reference.group(1)
        baby = identifier in babies
        male = fields.get("male") == "true"
        female = fields.get("female") == "true"
        stage = "baby" if baby else "adult" if male or female else ""
        # Large adults reuse baby artwork for live inventory pickup. Their
        # carcass icon is the representative adult image, as in slaughter logs.
        icon_field = "invIconBaby" if baby else "invIconMaleDead" if male else "invIconFemaleDead"
        choices = breeds.get(species, {})
        # Stable breed order provides representative art without claiming that
        # a species-level run statistic recorded the animal's breed.
        icon = next((choices[breed][icon_field] for breed in sorted(choices)
                     if choices[breed].get(icon_field)), "")
        yield ParsedAnimal(identifier, species, stage, icon)


def read_trapped_animals(path, items):
    """Resolve registered trapping types through their declared caught items."""
    if not path.exists():
        return
    fields, registered = {}, []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("--", 1)[0].strip()
        match = re.fullmatch(r'(\w+)\.(type|item)\s*=\s*"([^"\n]+)"\s*;?', line)
        if match:
            variable, key, value = match.groups()
            fields.setdefault(variable, {})[key] = value
        match = re.fullmatch(r'table\.insert\(TrapAnimals,\s*(\w+)\)\s*;?', line)
        if match:
            registered.append(match.group(1))
    from .item_artwork import item_icon_key
    for variable in registered:
        definition = fields.get(variable, {})
        identifier = definition.get("type")
        if not identifier:
            continue
        item = items.get(definition.get("item"))
        icon = item_icon_key(item.fields) if item else ""
        # Animal assets keep the game's full texture key, like husbandry icons.
        if icon and not icon.startswith("Item_"):
            icon = "Item_" + icon
        yield ParsedAnimal(identifier, identifier, "", icon)
