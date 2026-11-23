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


SICKNESS_FIELDS = {
    "foodSickness": ("food_sickness", 100),
    "poison": ("poison", 100),
    "corpseSicknessRate": ("corpse_sickness_rate", 1e308),
    "woundInfectionLevel": ("wound_infection_level", 100),
}


def sickness_fields(container):
    if "sickness" not in container:
        return {field: None for field, _ in SICKNESS_FIELDS.values()}
    value = container["sickness"]
    if not isinstance(value, dict) or set(value) != set(SICKNESS_FIELDS):
        raise ValueError("Invalid sickness evidence fields.")
    return {field: _number(value[key], 0, maximum)
            for key, (field, maximum) in SICKNESS_FIELDS.items()}


THERMAL_FIELDS = {
    "hypothermiaLevel": ("last_living_hypothermia_level", 4, True),
    "damageStage": ("last_living_thermal_damage_stage", 1, False),
    "observedUtc": ("last_living_thermal_utc", 2**63 - 1, True),
    "observedWorldAgeHours": ("last_living_thermal_world_age_hours", 1e12, False),
    "ageMilliseconds": ("last_living_thermal_age_milliseconds", 2**63 - 1, True),
}


def thermal_fields(evidence):
    result = {field: None for field, _, _ in THERMAL_FIELDS.values()}
    result["thermal_damage_stage_at_death"] = None
    if "lastLivingThermal" in evidence or "thermalDamageStageAtDeath" in evidence:
        if evidence.get("captureContext") != "death_callback":
            raise ValueError("Recovery cannot reconstruct thermal observations.")
    if "thermalDamageStageAtDeath" in evidence:
        result["thermal_damage_stage_at_death"] = _number(evidence["thermalDamageStageAtDeath"], 0, 1)
    if "lastLivingThermal" in evidence:
        value = evidence["lastLivingThermal"]
        if not isinstance(value, dict) or set(value) != set(THERMAL_FIELDS):
            raise ValueError("Invalid last living thermal observation.")
        for key, (field, maximum, integer) in THERMAL_FIELDS.items():
            number = _number(value[key], 0, maximum, integer=integer)
            result[field] = int(number) if integer else number
    return result


def medication_fields(evidence):
    result = {"sleeping_pills_taken": None, "intoxication_at_death": None}
    if "medication" not in evidence:
        return result
    value = evidence["medication"]
    if evidence.get("captureContext") != "death_callback":
        raise ValueError("Recovery cannot reconstruct medication at death.")
    if not isinstance(value, dict) or set(value) != {"sleepingPillsTaken", "intoxication"}:
        raise ValueError("Invalid medication evidence fields.")
    result["sleeping_pills_taken"] = int(_number(value["sleepingPillsTaken"], 0, 2**31 - 1, integer=True))
    result["intoxication_at_death"] = _number(value["intoxication"], 0, 100)
    return result



def wound_rows(evidence):
    if "terminalWounds" not in evidence:
        return []
    wounds = evidence["terminalWounds"]
    if evidence.get("captureContext") != "death_callback":
        raise ValueError("Recovery cannot reconstruct terminal wounds.")
    if not isinstance(wounds, list) or len(wounds) > 68:
        raise ValueError("Invalid terminal wounds.")
    rows, seen = [], set()
    for wound in wounds:
        if not isinstance(wound, dict) or set(wound) != {
            "injuryType", "bodyPart", "remainingTime", "bandaged", "bleedingTime", "zombieAssociation"
        }:
            raise ValueError("Invalid terminal wound fields.")
        kind = wound["injuryType"]
        part = _text(wound["bodyPart"], 32, empty=False)
        origin = wound["zombieAssociation"]
        if kind not in ("bite", "scratch", "laceration", "deep_wound"):
            raise ValueError("Invalid terminal wound type.")
        if origin not in ("bite", "observed_zombie_attack", "unknown") or ((kind == "bite") != (origin == "bite")):
            raise ValueError("Invalid terminal wound association.")
        if type(wound["bandaged"]) is not bool or (kind, part) in seen:
            raise ValueError("Invalid or duplicate terminal wound.")
        seen.add((kind, part))
        remaining = _number(wound["remainingTime"], 0, 1e308)
        if remaining <= 0:
            raise ValueError("Terminal wound must still be present.")
        rows.append(dict(injury_type=kind, body_part=part, remaining_time=remaining,
                         bandaged=wound["bandaged"], bleeding_time=_number(wound["bleedingTime"], 0, 1e308),
                         zombie_association=origin))
    return rows

def death_fields(evidence):
    if not isinstance(evidence, dict) or type(evidence.get("schema")) is not int or evidence["schema"] not in (1, 2, 3, 4):
        raise ValueError("Unsupported death evidence schema.")
    context = evidence.get("captureContext")
    if context not in ("death_callback", "recovery"):
        raise ValueError("Invalid death capture context.")
    if type(evidence.get("recentWindowMilliseconds")) is not int or evidence["recentWindowMilliseconds"] != 10000:
        raise ValueError("Invalid recent damage window.")
    for key in ("killedByFall", "deathDragDown", "infectedAtDeath"):
        if key in evidence and type(evidence[key]) is not bool:
            raise ValueError("Invalid terminal flag.")
    if context == "recovery" and "sickness" in evidence:
        raise ValueError("Recovery cannot reconstruct sickness at death.")
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
        if "sickness" in item and source not in ("SICK", "POISON"):
            raise ValueError("Unexpected sickness damage context.")
        sickness_fields(item)
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
    wounds = wound_rows(evidence)
    thermal = thermal_fields(evidence)
    medication = medication_fields(evidence)
    living = evidence.get("lastLivingThermal")
    fatal_hypothermia = (
        evidence["schema"] >= 2 and living is not None
        and living["hypothermiaLevel"] == 4 and living["ageMilliseconds"] <= 1000
        and 0 < living["damageStage"] < 1
        and evidence.get("thermalDamageStageAtDeath") == 1 and not last_source
    )
    fall, drag = evidence.get("killedByFall"), evidence.get("deathDragDown")
    fatal_pills = (evidence["schema"] >= 3
                   and medication["sleeping_pills_taken"] is not None
                   and medication["sleeping_pills_taken"] >= 12)
    competing_pills = fatal_pills and (
        fall or drag or last_source or evidence.get("thermalDamageStageAtDeath") == 1
    )
    pills_with_bleeding = (evidence["schema"] >= 4
                          and medication["sleeping_pills_taken"] is not None
                          and medication["sleeping_pills_taken"] >= 10
                          and "BLEEDING" in sources)
    if fall and drag:
        cause, certainty = "mixed", "conflicting_flags"
    elif competing_pills or pills_with_bleeding:
        cause, certainty = "mixed", "competing_evidence"
    elif fall:
        cause, certainty = "fall", "explicit_flag"
    elif drag:
        cause, certainty = "zombie_drag_down", "explicit_flag"
    elif fatal_pills:
        if fall is False and drag is False and evidence.get("thermalDamageStageAtDeath") is not None:
            cause, certainty = "sleeping_pills", "fatal_threshold"
        else:
            cause, certainty = "unknown", "unknown"
    elif fatal_hypothermia:
        cause, certainty = "hypothermia", "fatal_threshold"
    elif last_source:
        cause = "POISON" if last_source == "SICK" and "POISON" in sources else last_source
        if last_source == "BLEEDING" and any(
            not wound["bandaged"] and wound["bleeding_time"] > 0
            and wound["zombie_association"] != "unknown" for wound in wounds
        ):
            cause = "zombie_attack"
        certainty = "suspected"
    else:
        cause, certainty = "unknown", "unknown"
    if evidence.get("cause") != cause or evidence.get("certainty") != certainty:
        raise ValueError("Cause classification does not match evidence.")
    result = {
        "terminal_wounds_captured": "terminalWounds" in evidence,
        **sickness_fields(evidence),
        **medication,
        **thermal,
        "schema": evidence["schema"], "capture_context": context, "cause": cause,
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
