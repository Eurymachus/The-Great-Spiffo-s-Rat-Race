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


def _catalogue_map(kind, identifiers):
    identifiers = {str(value or "") for value in identifiers if value}
    candidates = identifiers | {
        f"base:{value}" for value in identifiers if ":" not in value
    }
    entries = CatalogueEntry.objects.filter(
        kind=kind,
        stable_id__in=candidates,
        is_active=True,
    ).select_related("trait_details")
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

    raw_skills = [
        skill for skill in projection.get("skills", []) if isinstance(skill, dict)
    ]
    skill_catalogue = _catalogue_map(
        CatalogueEntry.Kind.SKILL,
        (skill.get("id") for skill in raw_skills),
    )
    skill_details = {
        details.entry_id: details
        for details in SkillDetails.objects.filter(
            entry_id__in=(entry.pk for entry in skill_catalogue.values())
        )
    }
    skill_icons = _catalogue_icon_map(skill_catalogue.values())
    skills = []
    for skill in raw_skills:
        if not isinstance(skill, dict):
            continue
        skill_id = str(skill.get("id") or "")
        catalogue_entry = skill_catalogue.get(skill_id)
        details = skill_details.get(catalogue_entry.pk) if catalogue_entry else None
        level = skill.get("level", 0)
        xp = skill.get("xp")
        level_progress = _skill_level_progress(
            level,
            xp,
            details.level_xp if details else [],
        )
        category = (
            details.category
            if details and details.category
            else _name(skill.get("categoryId"))
        )
        skills.append(
            {
                "id": skill_id,
                "name": (
                    catalogue_entry.display_name
                    if catalogue_entry
                    else _name(skill_id)
                ),
                "icon_url": (
                    skill_icons.get(catalogue_entry.pk, "")
                    if catalogue_entry
                    else ""
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

    progress = []
    categories = projection.get("challengeProgress", {}).get("categories", {})
    if isinstance(categories, dict):
        for key, value in categories.items():
            if not isinstance(value, dict) or not value.get("available"):
                continue
            ratio = value.get("progress", 0)
            ratio = ratio if isinstance(ratio, (int, float)) else 0
            progress.append(
                {
                    "name": _name(key),
                    "current": value.get("current", 0),
                    "target": value.get("target", 0),
                    "current_display": f"{value.get('current', 0):,}",
                    "target_display": f"{value.get('target', 0):,}",
                    "percent": round(max(0, min(1, ratio)) * 100, 1),
                    "status": _name(value.get("status")),
                }
            )

    outposts = []
    for outpost in projection.get("outposts", []):
        if not isinstance(outpost, dict):
            continue
        ratio = outpost.get("progress", 0)
        ratio = ratio if isinstance(ratio, (int, float)) else 0
        outposts.append(
            {
                "name": _name(outpost.get("id")),
                "stage": _name(outpost.get("stage")),
                "percent": round(max(0, min(1, ratio)) * 100, 1),
                "complete": bool(outpost.get("complete")),
                "passed": outpost.get("passedRequirements", 0),
                "total": outpost.get("totalRequirements", 0),
            }
        )

    towns = []
    town_visits = projection.get("townVisits", {})
    if isinstance(town_visits, dict):
        towns = [
            {"name": _name(town.get("id")), "visited": bool(town.get("visited"))}
            for town in town_visits.get("towns", [])
            if isinstance(town, dict)
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
    profession_id = current_character.get("professionId")
    profession_catalogue = _catalogue_map(
        CatalogueEntry.Kind.OCCUPATION,
        (profession_id,),
    )
    catalogue_icons = _catalogue_icon_map(
        (*trait_catalogue.values(), *profession_catalogue.values())
    )
    profession_entry = profession_catalogue.get(str(profession_id))
    profession_icon_url = (
        catalogue_icons.get(profession_entry.pk, "") if profession_entry else ""
    )
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
        return {
            "name": entry.display_name if entry else _name(value),
            "icon_url": catalogue_icons.get(entry.pk, "") if entry else "",
            "point_cost": point_cost,
            "is_negative": point_cost is not None and point_cost < 0,
            "point_value": (
                f"{(-point_cost):+d}" if point_cost is not None else "?"
            ),
            "description": description or "No game description is available for this trait.",
        }

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
        "weight": (
            f"{weight.get('currentKilograms'):,.1f} kg"
            if isinstance(weight, dict)
            and isinstance(weight.get("currentKilograms"), (int, float))
            else "Not recorded"
        ),
        "selected_traits": [presented_trait(value) for value in selected_traits],
        "current_traits": [presented_trait(value) for value in current_traits],
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
