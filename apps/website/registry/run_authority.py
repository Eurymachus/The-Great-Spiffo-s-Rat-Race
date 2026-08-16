from zomboid_catalogue.models import CatalogueEntry, MapLocationVersion
from zomboid_catalogue.resolver import resolve_identifier

from .models import (
    RunCharacter,
    RunCharacterTrait,
    RunContractState,
    RunKillSummary,
    RunOutpost,
    RunOutpostDeliverable,
    RunSkill,
    RunStartingLocation,
    RunWeaponKill,
)


def _resolve(kind, raw_id):
    raw_id = str(raw_id or "")
    if not raw_id:
        return None
    resolved = resolve_identifier(kind, raw_id)
    if resolved or ":" in raw_id:
        return resolved
    return resolve_identifier(kind, f"base:{raw_id}")


def _snapshot(value):
    return value if isinstance(value, dict) else {}


def _lifecycle_fields(value):
    summary = _snapshot(value)
    fields = {
        "completion_count": int(summary.get("completionCount") or 0),
        "regression_count": int(summary.get("regressionCount") or 0),
        "current_state": str(summary.get("currentState") or "incomplete"),
    }
    for source, target in (
        ("firstCompletion", "first_completed"),
        ("latestCompletion", "latest_completed"),
        ("latestRegression", "latest_regressed"),
    ):
        point = _snapshot(summary.get(source))
        fields[f"{target}_sequence"] = point.get("sequence")
        fields[f"{target}_utc"] = point.get("utc")
        fields[f"{target}_world_age_hours"] = point.get("worldAgeHours")
        fields[f"{target}_elapsed_days"] = point.get("elapsedDays")
    return fields


def refresh_initial_run_authority(run, projection):
    character_projection = _snapshot(projection.get("character"))
    starting = _snapshot(character_projection.get("starting"))
    current = _snapshot(character_projection.get("current"))

    RunContractState.objects.update_or_create(
        run=run, defaults={"projection_schema": projection["schema"]}
    )
    character, _ = RunCharacter.objects.update_or_create(
        run=run,
        defaults={
            "starting_forename": str(starting.get("forename") or ""),
            "starting_surname": str(starting.get("surname") or ""),
            "starting_display_name": str(starting.get("displayName") or ""),
            "starting_occupation_raw_id": str(starting.get("professionId") or ""),
            "starting_occupation": _resolve(
                CatalogueEntry.Kind.OCCUPATION, starting.get("professionId")
            ),
            "current_forename": str(current.get("forename") or ""),
            "current_surname": str(current.get("surname") or ""),
            "current_display_name": str(current.get("displayName") or ""),
            "current_occupation_raw_id": str(current.get("professionId") or ""),
            "current_occupation": _resolve(
                CatalogueEntry.Kind.OCCUPATION, current.get("professionId")
            ),
            "selected_traits_partial": bool(
                character_projection.get("selectedStartingTraitsPartial", False)
            ),
            "selected_traits_captured_utc": character_projection.get(
                "selectedStartingTraitsCapturedUtc"
            ),
        },
    )
    character.traits.all().delete()
    phases = (
        (RunCharacterTrait.Phase.SELECTED_STARTING, "selectedStartingTraits"),
        (RunCharacterTrait.Phase.SPAWNED_STARTING, "startingEffectiveTraits"),
        (RunCharacterTrait.Phase.CURRENT, "currentEffectiveTraits"),
    )
    trait_rows = []
    for phase, key in phases:
        values = character_projection.get(key, [])
        if not isinstance(values, list):
            continue
        for position, raw_id in enumerate(values):
            raw_id = str(raw_id)
            trait_rows.append(
                RunCharacterTrait(
                    character=character,
                    raw_trait_id=raw_id,
                    catalogue_entry=_resolve(CatalogueEntry.Kind.TRAIT, raw_id),
                    phase=phase,
                    position=position,
                )
            )
    RunCharacterTrait.objects.bulk_create(trait_rows)

    chosen = _snapshot(character_projection.get("chosenStartingRegion"))
    observed = _snapshot(character_projection.get("startingLocation"))
    registered = _snapshot(observed.get("registeredLocation"))
    registered_kind = str(registered.get("kind") or "")
    registered_catalogue_kind = {
        "outpost": CatalogueEntry.Kind.OUTPOST,
        "landmark": CatalogueEntry.Kind.LOCATION,
    }.get(registered_kind)
    registered_entry = (
        _resolve(registered_catalogue_kind, registered.get("id"))
        if registered_catalogue_kind
        else None
    )
    map_version = None
    if registered_entry and registered.get("registryVersion"):
        map_version = MapLocationVersion.objects.filter(
            entry=registered_entry,
            registry_version=registered["registryVersion"],
        ).order_by("-game_version").first()
    RunStartingLocation.objects.update_or_create(
        run=run,
        defaults={
            "chosen_region_schema": chosen.get("schema"),
            "selection_mode": str(chosen.get("selectionMode") or ""),
            "resolved_region_raw_id": str(chosen.get("resolvedRegionId") or ""),
            "resolved_region_catalogue": _resolve(
                CatalogueEntry.Kind.TOWN, chosen.get("resolvedRegionId")
            ),
            "chosen_region_captured_utc": chosen.get("capturedUtc"),
            "x": observed.get("x"),
            "y": observed.get("y"),
            "z": observed.get("z"),
            "building_def_id": str(observed.get("buildingId") or ""),
            "captured_utc": observed.get("capturedUtc"),
            "world_age_hours": observed.get("worldAgeHours"),
            "partial": bool(observed.get("partial", False)),
            "registered_kind": registered_kind,
            "registered_raw_id": str(registered.get("id") or ""),
            "registry_version": registered.get("registryVersion"),
            "catalogue_entry": registered_entry,
            "map_location_version": map_version,
        },
    )

    RunOutpost.objects.filter(run=run).delete()
    for outpost_projection in projection.get("outposts", []):
        if not isinstance(outpost_projection, dict):
            continue
        raw_outpost_id = str(outpost_projection.get("id") or "")
        outpost = RunOutpost.objects.create(
            run=run,
            raw_outpost_id=raw_outpost_id,
            catalogue_entry=_resolve(CatalogueEntry.Kind.OUTPOST, raw_outpost_id),
            discovered=bool(outpost_projection.get("discovered", False)),
            discovered_world_age_hours=float(
                outpost_projection.get("discoveredWorldAgeHours") or 0
            ),
            stage=str(outpost_projection.get("stage") or "undiscovered"),
            complete=bool(outpost_projection.get("complete", False)),
            progress=float(outpost_projection.get("progress") or 0),
            passed_requirements=int(
                outpost_projection.get("passedRequirements") or 0
            ),
            total_requirements=int(
                outpost_projection.get("totalRequirements") or 0
            ),
            work_started_world_age_hours=float(
                outpost_projection.get("workStartedWorldAgeHours") or 0
            ),
            **_lifecycle_fields(outpost_projection.get("lifecycle")),
        )
        deliverable_rows = []
        for deliverable in outpost_projection.get("deliverables", []):
            if not isinstance(deliverable, dict):
                continue
            raw_deliverable_id = str(deliverable.get("id") or "")
            deliverable_rows.append(
                RunOutpostDeliverable(
                    outpost=outpost,
                    raw_deliverable_id=raw_deliverable_id,
                    catalogue_entry=_resolve(
                        CatalogueEntry.Kind.DELIVERABLE, raw_deliverable_id
                    ),
                    available=bool(deliverable.get("available", False)),
                    passed=bool(deliverable.get("passed", False)),
                    current_value=float(deliverable.get("current") or 0),
                    required_value=float(deliverable.get("required") or 0),
                    observed_state=str(deliverable.get("state") or ""),
                    progress=float(deliverable.get("progress") or 0),
                    observed_world_age_hours=float(
                        deliverable.get("observedWorldAgeHours") or 0
                    ),
                    **_lifecycle_fields(deliverable.get("lifecycle")),
                )
            )
        RunOutpostDeliverable.objects.bulk_create(deliverable_rows)

    RunSkill.objects.filter(run=run).delete()
    skill_rows = []
    for skill in projection.get("skills", []):
        if not isinstance(skill, dict):
            continue
        raw_skill_id = str(skill.get("id") or "")
        if not raw_skill_id:
            continue
        level = max(0, int(skill.get("level") or 0))
        xp = max(0, float(skill.get("xp") or 0))
        if level == 0 and xp == 0:
            continue
        skill_rows.append(
            RunSkill(
                run=run,
                raw_skill_id=raw_skill_id,
                raw_category_id=str(skill.get("categoryId") or ""),
                catalogue_entry=_resolve(CatalogueEntry.Kind.SKILL, raw_skill_id),
                level=level,
                xp=xp,
            )
        )
    RunSkill.objects.bulk_create(skill_rows)

    weapon_projection = _snapshot(projection.get("weaponKills"))
    fire_projection = _snapshot(projection.get("fireDeaths"))
    kill_types = _snapshot(projection.get("zombieKillTypes"))
    RunKillSummary.objects.update_or_create(
        run=run,
        defaults={
            "current_kills": max(0, int(projection.get("currentKills") or 0)),
            "weapon_partial": bool(weapon_projection.get("partial", False)),
            "weapon_baseline_total": max(
                0, int(weapon_projection.get("baselineTotal") or 0)
            ),
            "fire_deaths": max(0, int(fire_projection.get("count") or 0)),
            "fire_deaths_partial": bool(fire_projection.get("partial", False)),
            "zombie_kill_types_partial": bool(kill_types.get("partial", False)),
            "standing": max(0, int(kill_types.get("standing") or 0)),
            "on_front": max(0, int(kill_types.get("onfront") or 0)),
            "on_back": max(0, int(kill_types.get("onback") or 0)),
            "fence_assist": max(0, int(kill_types.get("fenceAssist") or 0)),
            "window_assist": max(0, int(kill_types.get("windowAssist") or 0)),
        },
    )
    RunWeaponKill.objects.filter(run=run).delete()
    weapon_rows = []
    for source in weapon_projection.get("sources", []):
        if not isinstance(source, dict):
            continue
        raw_source_id = str(source.get("id") or "")
        kills = max(0, int(source.get("kills") or 0))
        if not raw_source_id or kills == 0:
            continue
        weapon_rows.append(
            RunWeaponKill(
                run=run,
                raw_source_id=raw_source_id,
                catalogue_entry=_resolve(CatalogueEntry.Kind.ITEM, raw_source_id),
                kills=kills,
            )
        )
    RunWeaponKill.objects.bulk_create(weapon_rows)
