"""Successful farming actions and observed produce, independent of daily history."""
import re
from .cooked_food import items_counts, MAX_COUNT, MAX_ITEM_TYPES

FIELDS = {"planted": "farmingPlantedDeltas", "harvested": "farmingHarvestedDeltas", "produce": "farmingProduceDeltas"}
CROP_ID = re.compile(r"[A-Za-z0-9_.:-]+\Z")

def crop_counts(value):
    if value == []:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_ITEM_TYPES:
        raise ValueError("Invalid farming crop counts.")
    for key, count in value.items():
        if (not isinstance(key, str) or len(key) > 255 or not CROP_ID.fullmatch(key)
                or type(count) is not int or not 0 <= count <= MAX_COUNT):
            raise ValueError("Invalid farming crop/count.")
    if sum(value.values()) > MAX_COUNT:
        raise ValueError("Farming total is too large.")
    return value

def validate_farming(projection, events):
    source = projection.get("farming")
    if "farming" in projection:
        if (not isinstance(source, dict) or type(source.get("schema")) is not int
                or source["schema"] != 1 or set(source) - {"schema", "partial", *FIELDS}
                or ("partial" in source and type(source["partial"]) is not bool)):
            raise ValueError("Invalid farming snapshot.")
        totals = {key: (items_counts if key == "produce" else crop_counts)(source.get(key)) for key in FIELDS}
    else:
        totals = None
    days = [projection.get("activeDay")]
    days.extend(event.get("payload", {}).get("completedDay") for event in events if event.get("event_type") == "day.started")
    observed = {key: {} for key in FIELDS}
    for day in days:
        if not isinstance(day, dict):
            continue
        if "farmingPartial" in day and type(day["farmingPartial"]) is not bool:
            raise ValueError("Invalid farming coverage.")
        for key, field in FIELDS.items():
            if field not in day:
                continue
            counts = (items_counts if key == "produce" else crop_counts)(day[field])
            if totals is None:
                raise ValueError("Farming daily data requires cumulative coverage.")
            for raw_id, count in counts.items():
                observed[key][raw_id] = observed[key].get(raw_id, 0) + count
                if observed[key][raw_id] > totals[key].get(raw_id, 0):
                    raise ValueError("Farming daily counts exceed cumulative counts.")
