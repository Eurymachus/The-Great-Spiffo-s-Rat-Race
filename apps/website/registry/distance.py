"""Validation for independently sampled travel modes and daily deltas."""
import math

MODES = {"onFoot", "driver"}


def modes(value):
    if not isinstance(value, dict) or set(value) != MODES:
        raise ValueError("Invalid distance mode counters.")
    for number in value.values():
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 2**53 - 1:
            raise ValueError("Invalid distance value.")
    return value


def within(value, maximum):
    return value <= maximum + max(0.00001, abs(maximum) * 1e-8)


def validate_distance(projection, events):
    source = projection.get("distance", {})
    if not isinstance(source, dict):
        raise ValueError("Invalid distance snapshot.")
    totals = modes(source["byModeMeters"]) if "byModeMeters" in source else None
    if "modesPartial" in source and type(source["modesPartial"]) is not bool:
        raise ValueError("Invalid distance coverage.")
    if totals is not None:
        total = source.get("travelledMeters", 0)
        if type(total) not in (int, float) or not math.isfinite(total) or total < 0:
            raise ValueError("Invalid total distance.")
        split = sum(totals.values())
        if not within(split, total) or (not source.get("modesPartial") and not within(total, split)):
            raise ValueError("Distance modes disagree with total distance.")
    days = [projection.get("activeDay", {})]
    days += [event.get("payload", {}).get("completedDay", {}) for event in events
             if event.get("event_type") == "day.started"]
    observed = dict.fromkeys(MODES, 0.0)
    for day in days:
        if not isinstance(day, dict):
            continue
        if "distanceModesPartial" in day and type(day["distanceModesPartial"]) is not bool:
            raise ValueError("Invalid daily distance coverage.")
        if "distanceByModeDeltas" not in day:
            continue
        values = modes(day["distanceByModeDeltas"])
        if totals is None:
            raise ValueError("Daily distance modes require cumulative coverage.")
        total = day.get("distanceDeltaMeters", 0)
        if type(total) not in (int, float) or not math.isfinite(total) or total < 0:
            raise ValueError("Invalid daily total distance.")
        partial = day.get("distanceModesPartial") or "distanceModes" in day.get("partialMetrics", [])
        split = sum(values.values())
        if not within(split, total) or (not partial and not within(total, split)):
            raise ValueError("Daily distance modes disagree with total distance.")
        for mode, value in values.items():
            observed[mode] += value
            if not within(observed[mode], totals[mode]):
                raise ValueError("Daily distance exceeds cumulative distance.")
