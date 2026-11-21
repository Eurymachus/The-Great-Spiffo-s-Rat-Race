"""Versioned terminal observations, not a medically certain cause classifier."""

import math
from copy import deepcopy


def canonical_death_evidence(evidence):
    """Expand only the exporter's documented sparse false location flag."""
    death_fields(evidence)
    result = deepcopy(evidence)
    if isinstance(result.get("location"), dict):
        result["location"].setdefault("partial", False)
    return result


def _number(value, minimum, maximum, *, integer=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not minimum <= value <= maximum or (integer and value % 1)):
        raise ValueError("Invalid death evidence number.")
    return value


def _text(value, maximum, *, empty=True):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
        raise ValueError("Invalid death evidence text.")
    return value


def death_fields(evidence):
    if not isinstance(evidence, dict) or type(evidence.get("schema")) is not int or evidence["schema"] != 1:
        raise ValueError("Unsupported death evidence schema.")
    context = evidence.get("captureContext")
    if context not in ("death_callback", "recovery"):
        raise ValueError("Invalid death capture context.")
    if type(evidence.get("recentWindowMilliseconds")) is not int or evidence["recentWindowMilliseconds"] != 10000:
        raise ValueError("Invalid recent damage window.")
    for key in ("killedByFall", "deathDragDown", "infectedAtDeath"):
        if key in evidence and type(evidence[key]) is not bool:
            raise ValueError("Invalid terminal flag.")
    if context == "recovery" and "infectedAtDeath" in evidence:
        raise ValueError("Recovery cannot reconstruct infection at death.")
    if ("killedByFall" in evidence) != ("deathDragDown" in evidence):
        raise ValueError("Incomplete terminal flags.")
    recent = evidence.get("recentDamage")
    if not isinstance(recent, list) or len(recent) > 32:
        raise ValueError("Invalid recent damage observations.")
    sources = set()
    previous_age = 10000
    for item in recent:
        if not isinstance(item, dict):
            raise ValueError("Invalid damage observation.")
        source = _text(item.get("source"), 64, empty=False)
        if source in sources:
            raise ValueError("Duplicate damage source.")
        sources.add(source)
        _number(item.get("amount"), 0, 1e308)
        if item["amount"] <= 0:
            raise ValueError("Non-positive damage observation.")
        age = _number(item.get("ageMilliseconds"), 0, previous_age, integer=True)
        previous_age = age
    last_source = _text(evidence.get("lastDamageSource"), 64)
    if last_source != (recent[-1]["source"] if recent else ""):
        raise ValueError("Last damage source does not match observations.")
    if context == "recovery" and recent:
        raise ValueError("Recovery cannot reconstruct recent damage.")
    fall, drag = evidence.get("killedByFall"), evidence.get("deathDragDown")
    if fall and drag:
        cause, certainty = "mixed", "conflicting_flags"
    elif fall:
        cause, certainty = "fall", "explicit_flag"
    elif drag:
        cause, certainty = "zombie_drag_down", "explicit_flag"
    elif last_source:
        cause, certainty = last_source, "suspected"
    else:
        cause, certainty = "unknown", "unknown"
    if evidence.get("cause") != cause or evidence.get("certainty") != certainty:
        raise ValueError("Cause classification does not match evidence.")
    result = {
        "schema": 1, "capture_context": context, "cause": cause,
        "certainty": certainty, "last_damage_source": last_source,
        "killed_by_fall": fall, "death_drag_down": drag,
        "infected_at_death": evidence.get("infectedAtDeath"),
        "x": None, "y": None, "z": None, "building_def_id": "",
        "registered_kind": "", "registered_raw_id": "", "registry_version": None,
        "location_captured_utc": None, "location_world_age_hours": None,
    }
    location = evidence.get("location")
    if location is not None:
        if not isinstance(location, dict):
            raise ValueError("Invalid terminal location.")
        for key in ("x", "y", "z"):
            result[key] = int(_number(location.get(key), -(2**31), 2**31 - 1, integer=True))
        if type(location.get("partial", False)) is not bool or location.get("partial", False) != (context == "recovery"):
            raise ValueError("Invalid terminal location coverage.")
        result["building_def_id"] = _text(location.get("buildingId"), 160)
        result["location_captured_utc"] = int(_number(location.get("capturedUtc"), 0, 2**63 - 1, integer=True))
        result["location_world_age_hours"] = _number(location.get("worldAgeHours"), 0, 1e12)
        registered = location.get("registeredLocation")
        if registered is not None:
            if not isinstance(registered, dict) or registered.get("kind") not in ("outpost", "landmark"):
                raise ValueError("Invalid registered terminal location.")
            result["registered_kind"] = registered["kind"]
            result["registered_raw_id"] = _text(registered.get("id"), 255, empty=False)
            result["registry_version"] = int(_number(registered.get("registryVersion"), 1, 2**31 - 1, integer=True))
    return result
