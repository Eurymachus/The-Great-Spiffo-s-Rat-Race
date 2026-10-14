"""Normalize optional weather observations without inventing missing history."""
import math
from datetime import date


def temperature_fields(source):
    result = dict(
        temperature_minimum=None,
        temperature_maximum=None,
        temperature_minimum_observation={},
        temperature_maximum_observation={},
        temperature_partial=False,
    )
    if source is None:
        return result
    if (
        not isinstance(source, dict)
        or type(source.get("schema")) is not int
        or source.get("schema") != 1
        or source.get("unit") != "celsius"
        or source.get("source") != "outdoor_weather"
        or type(source.get("sampleIntervalGameMinutes")) is not int
        or source.get("sampleIntervalGameMinutes") != 1
    ):
        raise ValueError("Invalid outdoor temperature metadata.")
    if not isinstance(source.get("partial", False), bool):
        raise ValueError("Invalid temperature coverage flag.")
    result["temperature_partial"] = source.get("partial", False)
    for key in ("minimum", "maximum"):
        observation = source.get(key)
        if observation is None:
            if source.get("minimum") is not None or source.get("maximum") is not None:
                raise ValueError("Incomplete temperature extremes.")
            continue
        if not isinstance(observation, dict):
            raise ValueError("Invalid temperature observation.")
        for field in ("celsius", "utc", "worldAgeHours", "timeOfDay"):
            value = observation.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("Invalid temperature observation number.")
        if (
            not 0 <= observation["utc"] < 2**63
            or observation["utc"] % 1
            or observation["worldAgeHours"] < 0
            or not 0 <= observation["timeOfDay"] < 24
        ):
            raise ValueError("Invalid temperature observation time.")
        calendar = observation.get("calendar")
        if not isinstance(calendar, dict) or any(
            type(calendar.get(k)) is not int for k in ("year", "month", "day")
        ):
            raise ValueError("Invalid temperature observation calendar.")
        date(calendar["year"], calendar["month"], calendar["day"])
        result[f"temperature_{key}"] = observation["celsius"]
        result[f"temperature_{key}_observation"] = observation
    if (
        result["temperature_minimum"] is not None
        and result["temperature_minimum"] > result["temperature_maximum"]
    ):
        raise ValueError("Temperature minimum exceeds maximum.")
    return result
