"""Language-independent item-type counts for collected cooked food items."""

import re

ITEM_ID = re.compile(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+\Z")
MAX_COUNT = 2**53 - 1
MAX_ITEM_TYPES = 4096


def items_counts(value):
    # The Lua canonical codec serializes an empty table as an empty array.
    if value == []:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_ITEM_TYPES:
        raise ValueError("Invalid cooked food item counts.")
    for item_id, count in value.items():
        if (not isinstance(item_id, str) or len(item_id) > 255
                or not ITEM_ID.fullmatch(item_id)
                or type(count) is not int or not 0 <= count <= MAX_COUNT):
            raise ValueError("Invalid cooked food item/count.")
    if sum(value.values()) > MAX_COUNT:
        raise ValueError("Cooked food total is too large.")
    return value


def validate_cooked_food(projection, events):
    source = projection.get("cookedFood")
    if "cookedFood" in projection:
        if (not isinstance(source, dict) or type(source.get("schema")) is not int
                or source["schema"] != 1
                or set(source) - {"schema", "items", "partial"}
                or ("partial" in source and type(source["partial"]) is not bool)):
            raise ValueError("Invalid cooked food snapshot.")
        totals = items_counts(source.get("items"))
    else:
        totals = None
    days = []
    active = projection.get("activeDay")
    if isinstance(active, dict):
        days.append(active)
    for event in events:
        if event.get("event_type") == "day.started":
            day = event.get("payload", {}).get("completedDay")
            if isinstance(day, dict):
                days.append(day)
    observed = {}
    for day in days:
        if "cookedFoodPartial" in day and type(day["cookedFoodPartial"]) is not bool:
            raise ValueError("Invalid cooked food coverage.")
        if "cookedFoodItemsDeltas" not in day:
            continue
        counts = items_counts(day["cookedFoodItemsDeltas"])
        if totals is None:
            raise ValueError("Cooked food daily data requires cumulative coverage.")
        for item_id, count in counts.items():
            observed[item_id] = observed.get(item_id, 0) + count
            if observed[item_id] > totals.get(item_id, 0):
                raise ValueError("Cooked food daily counts exceed cumulative counts.")
