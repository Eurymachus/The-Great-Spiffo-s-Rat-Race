"""Language-independent item-type counts for completed leisure reading actions."""

import re

ITEM_ID = re.compile(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+\Z")
MAX_COUNT = 2**53 - 1
MAX_ITEM_TYPES = 4096


def literature_counts(value):
    # The Lua canonical codec serializes an empty table as an empty array.
    if value == []:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_ITEM_TYPES:
        raise ValueError("Invalid entertainment literature counts.")
    for item_id, count in value.items():
        if (not isinstance(item_id, str) or len(item_id) > 255
                or not ITEM_ID.fullmatch(item_id)
                or type(count) is not int or not 0 <= count <= MAX_COUNT):
            raise ValueError("Invalid entertainment literature item/count.")
    if sum(value.values()) > MAX_COUNT:
        raise ValueError("Entertainment total is too large.")
    return value


def validate_entertainment(projection, events):
    source = projection.get("entertainment")
    if (not isinstance(source, dict)
            or set(source) != {"literature"}):
        raise ValueError("Invalid entertainment snapshot.")
    totals = literature_counts(source.get("literature"))
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
        partial_metrics = day.get("partialMetrics")
        if "entertainmentPartial" in day or (
                isinstance(partial_metrics, list) and "entertainment" in partial_metrics):
            raise ValueError("Entertainment partial coverage is unsupported.")
        counts = literature_counts(day.get("entertainmentLiteratureDeltas"))
        for item_id, count in counts.items():
            observed[item_id] = observed.get(item_id, 0) + count
            if observed[item_id] > totals.get(item_id, 0):
                raise ValueError("Entertainment daily counts exceed cumulative counts.")
