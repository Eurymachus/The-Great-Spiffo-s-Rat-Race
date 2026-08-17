import re

from django.utils.html import strip_tags
from django.templatetags.static import static
from zomboid_catalogue.models import (
    CatalogueAsset,
    CatalogueEntry,
    SkillDetails,
    version_key,
)


DISPLAY_NAMES = {
    "fastlearner": "Fast Learner",
    "needslesssleep": "Needs Less Sleep",
    "nightvision": "Night Vision",
    "pronetoillness": "Prone to Illness",
    "slowhealer": "Slow Healer",
    "slowreader": "Slow Reader",
    "thinskinned": "Thin-skinned",
    "weakstomach": "Weak Stomach",
    "weightgain": "Weight Gain",
    "wildernessknowledge": "Wilderness Knowledge",
}
SKILL_CATEGORY_LABELS = {
    "Firearm": "Combat - Firearms",
    "Combat": "Combat - Melee",
    "Crafting": "Crafting",
    "Farming": "Farming",
    "Physical": "Physical",
    "Survival": "Survival",
    "Survivalist": "Survival",
}
SKILL_CATEGORY_ORDER = {
    label: index
    for index, label in enumerate(
        (
            "Combat - Firearms",
            "Combat - Melee",
            "Crafting",
            "Farming",
            "Physical",
            "Survival",
        )
    )
}


def _name(value):
    value = str(value or "")
    if value == "__UNARMED__":
        return "Unarmed"
    value = value.rsplit(":", 1)[-1].rsplit(".", 1)[-1]
    if value.casefold() in DISPLAY_NAMES:
        return DISPLAY_NAMES[value.casefold()]
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = value.replace("_", " ").strip().title()
    return value.removesuffix(" Category") or "Unknown"


def _number(value, digits=1):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return f"{value:,.{digits}f}"


def _total(projection, key):
    value = projection.get(key, {})
    return value.get("total") if isinstance(value, dict) else None


def _outpost_number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "0"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"


def _outpost_deliverable_status(deliverable):
    state = str(deliverable.observed_state or "").strip()
    if state:
        return _name(state)
    if not deliverable.available:
        return "Unavailable"
    return (
        f"{_outpost_number(deliverable.current_value)} / "
        f"{_outpost_number(deliverable.required_value)}"
    )


OUTPOST_DELIVERABLE_PRESENTATION = {
    "room_activation": (1, "Room activation"),
    "floor_activation": (2, "Floor activation"),
    "zombie_clearance": (3, "Area Cleared"),
    "window_barricades": (4, "Window barricades"),
    "enclosed": (5, "Enclosed"),
    "doors_fitted": (6, "Doors fitted"),
    "doors_closed": (7, "Doors closed"),
    "good_bed": (8, "Good bed"),
    "generator": (9, "Generator"),
    "food": (10, "Food"),
    "plumbed_sink": (11, "Sink"),
    "spare_car": (12, "Spare car"),
    "engine_start": (13, "Spare car started"),
}
OUTPOST_REQUIREMENT_TOTAL = 14
TOWN_PRESENTATION_CATALOGUE = (
    ("brandenburg", "Brandenburg"),
    ("echo_creek", "Echo Creek"),
    ("ekron", "Ekron"),
    ("fallas_lake", "Fallas Lake"),
    ("irvington", "Irvington"),
    ("louisville", "Louisville"),
    ("march_ridge", "March Ridge"),
    ("muldraugh", "Muldraugh"),
    ("riverside", "Riverside"),
    ("rosewood", "Rosewood"),
    ("valley_station", "Valley Station"),
    ("west_point", "West Point"),
)


def _presented_outpost_deliverables(outpost):
    rows = [
        {
            "name": "Discovery",
            "value": "-",
            "passed": True,
            "status": "Passed",
            "status_class": "passed",
            "order": 0,
        }
    ]
    for deliverable in outpost.deliverables.all():
        order, fallback_name = OUTPOST_DELIVERABLE_PRESENTATION.get(
            deliverable.raw_deliverable_id,
            (99, _name(deliverable.raw_deliverable_id)),
        )
        rows.append(
            {
                "name": fallback_name,
                "value": _outpost_deliverable_status(deliverable),
                "passed": deliverable.passed,
                "status": (
                    "Passed"
                    if deliverable.passed
                    else "Pending" if deliverable.available else "Unavailable"
                ),
                "status_class": (
                    "passed"
                    if deliverable.passed
                    else "pending" if deliverable.available else "unavailable"
                ),
                "order": order,
            }
        )
    return sorted(rows, key=lambda row: (row["order"], row["name"]))


def _catalogue_map(kind, identifiers):
    identifiers = {str(value or "") for value in identifiers if value}
    candidates = identifiers | {
        f"base:{value}" for value in identifiers if ":" not in value
    }
    entries = CatalogueEntry.objects.filter(
        kind=kind,
        stable_id__in=candidates,
        is_active=True,
    ).select_related("trait_details", "occupation_details")
    resolved = {}
    for entry in sorted(entries, key=lambda item: version_key(item.introduced_in)):
        resolved[entry.stable_id] = entry
        if entry.stable_id.startswith("base:"):
            resolved[entry.stable_id.removeprefix("base:")] = entry
    return resolved


def _catalogue_icon_map(entries):
    entry_ids = {entry.pk for entry in entries if entry}
    if not entry_ids:
        return {}
    assets = CatalogueAsset.objects.filter(
        entry_id__in=entry_ids,
        role=CatalogueAsset.Role.ICON,
        availability=CatalogueAsset.Availability.IMPORTED,
        source_type__in=(
            CatalogueAsset.SourceType.PZWIKI,
            CatalogueAsset.SourceType.MANUAL,
        ),
    ).exclude(file="")
    source_priority = {
        CatalogueAsset.SourceType.PZWIKI: 1,
        CatalogueAsset.SourceType.MANUAL: 2,
    }
    resolved = {}
    priorities = {}
    for asset in assets:
        priority = source_priority[asset.source_type]
        if priority >= priorities.get(asset.entry_id, 0):
            resolved[asset.entry_id] = asset.file.url
            priorities[asset.entry_id] = priority
    return resolved


def _latest_catalogue_entries(kind):
    latest = {}
    for entry in CatalogueEntry.objects.filter(kind=kind, is_active=True):
        current = latest.get(entry.stable_id.casefold())
        if current is None or version_key(entry.introduced_in) > version_key(
            current.introduced_in
        ):
            latest[entry.stable_id.casefold()] = entry
    return latest


def _skill_level_progress(level, xp, thresholds):
    level = max(0, min(10, int(level or 0)))
    if level >= 10 or not isinstance(xp, (int, float)) or len(thresholds) < 10:
        return float(level)
    completed_xp = sum(thresholds[:level])
    next_level_xp = thresholds[level]
    fraction = (xp - completed_xp) / next_level_xp if next_level_xp else 0
    return level + max(0, min(1, fraction))


def build_public_run_context(run):
    approved_projection = (
        run.approved_submission.projection
        if run.approved_submission_id
        and isinstance(run.approved_submission.projection, dict)
        else {}
    )
    projection = approved_projection
    character = projection.get("character", {})
    current_character = character.get("current", {}) if isinstance(character, dict) else {}
    weight = projection.get("weight", {})
    distance = projection.get("distance", {})
    injuries = projection.get("injuries", {})
    all_injuries = injuries.get("all", {}) if isinstance(injuries, dict) else {}
    gameplay = projection.get("activeGameplay", {})
    nimble = projection.get("nimbleStance", {})
    starting_location = getattr(run, "starting_location", None)
    spawn_choice = "Not recorded"
    starting_coordinates = "Not recorded"
    starting_map_url = ""
    starting_map_icon_url = ""
    if starting_location:
        if starting_location.selection_mode == "random":
            spawn_choice = "Random Spawn, KY"
        elif starting_location.resolved_region_catalogue_id:
            spawn_choice = starting_location.resolved_region_catalogue.display_name
        elif starting_location.resolved_region_raw_id:
            spawn_choice = starting_location.resolved_region_raw_id
        if starting_location.x is not None and starting_location.y is not None:
            starting_coordinates = f"{starting_location.x}, {starting_location.y}"
            if starting_location.z is not None:
                starting_map_url = (
                    "https://map.projectzomboid.com?"
                    f"{starting_location.x}x{starting_location.y}x{starting_location.z}"
                )

    map_entries = list(
        CatalogueEntry.objects.filter(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.Map",
            is_active=True,
        )
    )
    if map_entries:
        map_entry = max(map_entries, key=lambda item: version_key(item.introduced_in))
        starting_map_icon_url = _catalogue_icon_map((map_entry,)).get(
            map_entry.pk, ""
        )

    skill_catalogue = _latest_catalogue_entries(CatalogueEntry.Kind.SKILL)
    skill_details = {
        details.entry_id: details
        for details in SkillDetails.objects.filter(
            entry_id__in=(entry.pk for entry in skill_catalogue.values())
        )
    }
    skill_icons = _catalogue_icon_map(skill_catalogue.values())
    authoritative_skills = {
        skill.raw_skill_id.casefold(): skill
        for skill in run.authoritative_skills.select_related("catalogue_entry")
    }
    skills = []
    for stable_id, catalogue_entry in skill_catalogue.items():
        skill = authoritative_skills.get(stable_id)
        skill_id = catalogue_entry.stable_id
        details = skill_details.get(catalogue_entry.pk)
        level = skill.level if skill else 0
        xp = skill.xp if skill else 0
        level_progress = _skill_level_progress(
            level,
            xp,
            details.level_xp if details else [],
        )
        category = (
            details.category
            if details and details.category
            else _name(skill.raw_category_id if skill else "")
        )
        skills.append(
            {
                "id": skill_id,
                "name": (
                    catalogue_entry.display_name
                ),
                "icon_url": (
                    skill_icons.get(catalogue_entry.pk, "")
                ),
                "category": SKILL_CATEGORY_LABELS.get(category, category),
                "level": level,
                "xp": _number(xp),
                "level_progress": level_progress,
                "segments": [
                    {"number": number, "filled": number <= int(level or 0)}
                    for number in range(1, 11)
                ],
                "mastered": int(level or 0) >= 10,
            }
        )
    skills.sort(
        key=lambda item: (
            SKILL_CATEGORY_ORDER.get(item["category"], 99),
            item["name"],
        )
    )
    skill_groups = []
    for skill in skills:
        if not skill_groups or skill_groups[-1]["name"] != skill["category"]:
            skill_groups.append({"name": skill["category"], "skills": []})
        skill_groups[-1]["skills"].append(skill)
    for group in skill_groups:
        group["mastered"] = sum(skill["mastered"] for skill in group["skills"])
        group["count"] = len(group["skills"])
        group["progress"] = sum(
            skill["level_progress"] for skill in group["skills"]
        )
        group["target"] = group["count"] * 10
        group["percent"] = round(
            (group["progress"] / group["target"] * 100) if group["target"] else 0,
            1,
        )
        group["progress_display"] = f"{group['progress']:.1f}".rstrip("0").rstrip(".")
    mastered_skills = sum(skill["mastered"] for skill in skills)
    overall_skill_progress = sum(skill["level_progress"] for skill in skills)
    overall_skill_target = len(skills) * 10

    outposts = []
    authoritative_outposts = list(
        run.authoritative_outposts.filter(discovered=True)
        .select_related("catalogue_entry")
        .prefetch_related("deliverables__catalogue_entry")
        .order_by("raw_outpost_id")
    )
    if authoritative_outposts:
        outposts = [
            {
                "id": (
                    outpost.catalogue_entry.stable_id
                    if outpost.catalogue_entry_id
                    else outpost.raw_outpost_id
                ),
                "name": (
                    outpost.catalogue_entry.display_name
                    if outpost.catalogue_entry_id
                    else _name(outpost.raw_outpost_id)
                ),
                "stage": _name(outpost.stage),
                "percent": round(max(0, min(1, outpost.progress)) * 100, 1),
                "complete": outpost.complete,
                "passed": outpost.passed_requirements,
                "total": outpost.total_requirements,
                "completion_count": outpost.completion_count,
                "regression_count": outpost.regression_count,
                "deliverables": _presented_outpost_deliverables(outpost),
                "discovered": True,
            }
            for outpost in authoritative_outposts
        ]
    else:
        for outpost in projection.get("outposts", []):
            if not isinstance(outpost, dict):
                continue
            ratio = outpost.get("progress", 0)
            ratio = ratio if isinstance(ratio, (int, float)) else 0
            stage = str(outpost.get("stage") or "").casefold()
            if outpost.get("discovered") is False or (
                "discovered" not in outpost
                and ratio <= 0
                and stage in {"", "unexplored", "undiscovered"}
            ):
                continue
            outposts.append(
                {
                    "id": str(outpost.get("id") or ""),
                    "name": _name(outpost.get("id")),
                    "stage": _name(outpost.get("stage")),
                    "percent": round(max(0, min(1, ratio)) * 100, 1),
                    "complete": bool(outpost.get("complete")),
                    "passed": outpost.get("passedRequirements", 0),
                    "total": outpost.get("totalRequirements", 0),
                    "completion_count": 0,
                    "regression_count": 0,
                    "deliverables": [],
                    "discovered": True,
                }
            )

    latest_outpost_entries = _latest_catalogue_entries(CatalogueEntry.Kind.OUTPOST)

    presented_outpost_ids = {
        str(outpost.get("id") or "").casefold() for outpost in outposts
    }
    for stable_id, entry in latest_outpost_entries.items():
        if stable_id in presented_outpost_ids:
            continue
        outposts.append(
            {
                "id": entry.stable_id,
                "name": entry.display_name,
                "stage": "Undiscovered",
                "percent": 0,
                "complete": False,
                "passed": 0,
                "total": OUTPOST_REQUIREMENT_TOTAL,
                "completion_count": 0,
                "regression_count": 0,
                "deliverables": [],
                "discovered": False,
            }
        )
    def outpost_status_order(outpost):
        if outpost["complete"]:
            return 0
        if outpost["discovered"]:
            return 1
        return 2

    outposts.sort(
        key=lambda outpost: (
            outpost_status_order(outpost),
            outpost["name"].casefold(),
            outpost["id"],
        )
    )
    kill_summary = getattr(run, "kill_summary", None)
    current_kills = kill_summary.current_kills if kill_summary else run.current_kills
    completed_outposts = sum(outpost["complete"] for outpost in outposts)
    landmark_catalogue = _latest_catalogue_entries(CatalogueEntry.Kind.LOCATION)
    visited_landmarks = run.authoritative_landmarks.count()

    progress_values = (
        ("kills", current_kills, 1_000_000, None),
        (
            "skills",
            mastered_skills,
            len(skills),
            overall_skill_progress / overall_skill_target
            if overall_skill_target
            else 0,
        ),
        ("outposts", completed_outposts, len(latest_outpost_entries), None),
        ("landmarks", visited_landmarks, len(landmark_catalogue), None),
    )
    progress = []
    for key, current, target, ratio_override in progress_values:
        if target <= 0:
            continue
        ratio = max(
            0,
            min(1, ratio_override if ratio_override is not None else current / target),
        )
        progress.append(
            {
                "id": key,
                "name": _name(key),
                "current": current,
                "target": target,
                "current_display": f"{current:,}",
                "target_display": f"{target:,}",
                "percent": round(ratio * 100, 1),
                "status": "Complete" if ratio >= 1 else "In Progress",
            }
        )

    towns = []
    town_visits = projection.get("townVisits", {})
    if isinstance(town_visits, dict):
        observed_towns = {
            str(town.get("id") or "").casefold(): town
            for town in town_visits.get("towns", [])
            if isinstance(town, dict)
        }
        towns = [
            {
                "id": stable_id,
                "name": display_name,
                "visited": bool(observed_towns.get(stable_id, {}).get("visited")),
            }
            for stable_id, display_name in TOWN_PRESENTATION_CATALOGUE
        ]

    distance_metres = distance.get("travelledMeters") if isinstance(distance, dict) else None
    activity = [
        {
            "label": "Distance travelled",
            "value": (
                f"{distance_metres / 1000:,.2f} km"
                if isinstance(distance_metres, (int, float))
                else "Not recorded"
            ),
        },
        {
            "label": "Tracked active play",
            "value": (
                f"{gameplay.get('milliseconds', 0) / 3_600_000:,.1f} hours"
                if isinstance(gameplay, dict)
                and isinstance(gameplay.get("milliseconds"), (int, float))
                else "Not recorded"
            ),
        },
        {
            "label": "Nimble stance movement",
            "value": (
                f"{nimble.get('movementMilliseconds', 0) / 60_000:,.1f} minutes"
                if isinstance(nimble, dict)
                and isinstance(nimble.get("movementMilliseconds"), (int, float))
                else "Not recorded"
            ),
        },
        {"label": "Recorded injuries", "value": all_injuries.get("total", 0)},
        {"label": "Fish caught", "value": _total(projection, "fishCaught")},
        {"label": "Animals trapped", "value": _total(projection, "animalsTrapped")},
        {
            "label": "Animals slaughtered",
            "value": _total(projection, "animalsSlaughtered"),
        },
        {"label": "Animal births", "value": _total(projection, "animalBirths")},
        {"label": "Broken weapons", "value": _total(projection, "brokenWeapons")},
        {
            "label": "Milk collected",
            "value": f"{_total(projection, 'milkCollected') or 0:,.1f} L",
        },
        {
            "label": "Butter produced",
            "value": projection.get("butterProduced", {}).get("count", 0),
        },
        {
            "label": "Fire deaths",
            "value": projection.get("fireDeaths", {}).get("count", 0),
        },
    ]

    selected_traits = character.get("selectedStartingTraits", []) if isinstance(character, dict) else []
    current_traits = character.get("currentEffectiveTraits", []) if isinstance(character, dict) else []
    trait_catalogue = _catalogue_map(
        CatalogueEntry.Kind.TRAIT,
        (*selected_traits, *current_traits),
    )
    trait_effect_skill_ids = {
        skill_id
        for entry in trait_catalogue.values()
        for skill_id in (
            getattr(getattr(entry, "trait_details", None), "xp_boosts", {}) or {}
        )
    }
    trait_effect_skill_catalogue = _catalogue_map(
        CatalogueEntry.Kind.SKILL,
        trait_effect_skill_ids,
    )
    starting_character = character.get("starting", {}) if isinstance(character, dict) else {}
    character_record = getattr(run, "character_record", None)
    profession_id = (
        character_record.starting_occupation_raw_id
        if character_record and character_record.starting_occupation_raw_id
        else starting_character.get("professionId") or current_character.get("professionId")
    )
    profession_catalogue = _catalogue_map(
        CatalogueEntry.Kind.OCCUPATION,
        (profession_id,),
    )
    catalogue_icons = _catalogue_icon_map(
        (*trait_catalogue.values(), *profession_catalogue.values())
    )
    profession_entry = (
        character_record.starting_occupation
        if character_record and character_record.starting_occupation_id
        else profession_catalogue.get(str(profession_id))
    )
    profession_icon_url = (
        catalogue_icons.get(profession_entry.pk, "") if profession_entry else ""
    )
    profession_details = (
        getattr(profession_entry, "occupation_details", None)
        if profession_entry
        else None
    )
    profession_point_cost = (
        profession_details.point_cost if profession_details else None
    )
    weapon_sources = projection.get("weaponKills", {}).get("sources", [])
    weapon_sources = [
        source
        for source in weapon_sources
        if isinstance(source, dict)
        and source.get("id")
        and isinstance(source.get("kills"), (int, float))
    ]
    favourite_weapon_source = max(
        weapon_sources,
        key=lambda source: (source.get("kills", 0), str(source.get("id"))),
        default=None,
    )
    favourite_weapon_id = (
        favourite_weapon_source.get("id") if favourite_weapon_source else None
    )
    weapon_catalogue = _catalogue_map(
        CatalogueEntry.Kind.ITEM,
        (favourite_weapon_id,),
    )
    favourite_weapon_entry = weapon_catalogue.get(str(favourite_weapon_id))
    weapon_icons = _catalogue_icon_map(weapon_catalogue.values())
    favourite_weapon = {
        "name": (
            favourite_weapon_entry.display_name
            if favourite_weapon_entry
            else _name(favourite_weapon_id) if favourite_weapon_id else "Not recorded"
        ),
        "kills": (
            int(favourite_weapon_source.get("kills", 0))
            if favourite_weapon_source
            else None
        ),
        "icon_url": (
            weapon_icons.get(favourite_weapon_entry.pk, "")
            if favourite_weapon_entry
            else ""
        ),
    }
    if not profession_icon_url and str(profession_id).casefold() in (
        "unemployed",
        "base:unemployed",
    ):
        profession_icon_url = static("registry/images/Profession_custom.png")

    def presented_trait(value):
        entry = trait_catalogue.get(value)
        details = getattr(entry, "trait_details", None) if entry else None
        point_cost = details.point_cost if details else None
        description = ""
        if details and details.description:
            description = strip_tags(
                re.sub(r"<br\s*/?>", "\n", details.description, flags=re.IGNORECASE)
            ).strip()
        if not description and details and details.xp_boosts:
            effects = []
            for skill_id, amount in details.xp_boosts.items():
                skill_entry = trait_effect_skill_catalogue.get(str(skill_id))
                skill_name = (
                    skill_entry.display_name if skill_entry else _name(skill_id)
                )
                effects.append(f"{amount:+g} {skill_name}")
            if len(effects) == 1:
                description = f"Starts with {effects[0]}."
            else:
                description = (
                    f"Starts with {', '.join(effects[:-1])} and {effects[-1]}."
                )
        return {
            "stable_id": str(value),
            "name": entry.display_name if entry else _name(value),
            "icon_url": catalogue_icons.get(entry.pk, "") if entry else "",
            "point_cost": point_cost,
            "is_negative": point_cost is not None and point_cost < 0,
            "is_passive": point_cost == 0,
            "point_value": (
                f"{point_cost:+d}" if point_cost is not None else "?"
            ),
            "description": description or "No game description is available for this trait.",
        }

    presented_selected_traits = [presented_trait(value) for value in selected_traits]
    presented_current_traits = [presented_trait(value) for value in current_traits]
    selected_trait_ids = {trait["stable_id"] for trait in presented_selected_traits}
    current_trait_ids = {trait["stable_id"] for trait in presented_current_traits}
    for trait in presented_current_traits:
        trait["change"] = (
            "retained" if trait["stable_id"] in selected_trait_ids else "gained"
        )
    removed_traits = [
        {**trait, "change": "lost"}
        for trait in presented_selected_traits
        if trait["stable_id"] not in current_trait_ids
    ]

    def trait_sort_key(trait):
        point_cost = trait["point_cost"]
        return (
            point_cost is None,
            point_cost if point_cost is not None else 0,
            trait["name"].casefold(),
        )

    def grouped_traits(traits):
        return (
            sorted(
                (trait for trait in traits if trait["is_negative"]),
                key=trait_sort_key,
            ),
            sorted(
                (trait for trait in traits if not trait["is_negative"]),
                key=trait_sort_key,
            ),
        )

    selected_negative_traits, selected_positive_traits = grouped_traits(
        presented_selected_traits
    )
    current_negative_traits, current_positive_traits = grouped_traits(
        presented_current_traits
    )
    removed_negative_traits, removed_positive_traits = grouped_traits(removed_traits)

    return {
        "run": run,
        "current_kills_display": f"{run.current_kills:,}",
        "rat_racer": run.participant.nickname if run.participant_id else "Former Rat Racer",
        "profession": (
            profession_entry.display_name
            if profession_entry
            else _name(profession_id)
        ),
        "profession_icon_url": profession_icon_url,
        "profession_point_value": (
            f"{profession_point_cost:+d}"
            if profession_point_cost is not None
            else None
        ),
        "profession_point_is_negative": (
            profession_point_cost is not None and profession_point_cost < 0
        ),
        "favourite_weapon": favourite_weapon,
        "weight": (
            f"{weight.get('currentKilograms'):,.1f} kg"
            if isinstance(weight, dict)
            and isinstance(weight.get("currentKilograms"), (int, float))
            else "Not recorded"
        ),
        "spawn_choice": spawn_choice,
        "starting_coordinates": starting_coordinates,
        "starting_map_url": starting_map_url,
        "starting_map_icon_url": starting_map_icon_url,
        "selected_traits": presented_selected_traits,
        "selected_negative_traits": selected_negative_traits,
        "selected_positive_traits": selected_positive_traits,
        "current_traits": presented_current_traits,
        "current_negative_traits": current_negative_traits,
        "current_positive_traits": current_positive_traits,
        "removed_negative_traits": removed_negative_traits,
        "removed_positive_traits": removed_positive_traits,
        "progress": progress,
        "skills": skills,
        "skill_groups": skill_groups,
        "mastered_skills": mastered_skills,
        "overall_skill_count": len(skills),
        "overall_skill_percent": round(
            (
                overall_skill_progress / overall_skill_target * 100
                if overall_skill_target
                else 0
            ),
            1,
        ),
        "outposts": outposts,
        "towns": towns,
        "visited_town_count": sum(town["visited"] for town in towns),
        "activity": activity,
    }
