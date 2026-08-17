from django.db import migrations


def backfill_run_landmarks(apps, schema_editor):
    ChallengeRun = apps.get_model("registry", "ChallengeRun")
    RunLandmark = apps.get_model("registry", "RunLandmark")
    CatalogueEntry = apps.get_model("zomboid_catalogue", "CatalogueEntry")

    catalogue = {
        entry.stable_id: entry
        for entry in CatalogueEntry.objects.filter(kind="location", is_active=True)
    }
    rows = []
    runs = ChallengeRun.objects.filter(approved_submission__isnull=False).select_related(
        "approved_submission"
    )
    for run in runs.iterator():
        projection = run.approved_submission.projection
        locations = projection.get("locations", {}) if isinstance(projection, dict) else {}
        if not isinstance(locations, dict):
            continue
        for location in locations.get("entries", []):
            if not isinstance(location, dict) or not location.get("visited"):
                continue
            raw_location_id = str(location.get("id") or "")
            first_visit = location.get("firstVisit") or {}
            if not raw_location_id or not isinstance(first_visit, dict):
                continue
            rows.append(
                RunLandmark(
                    run=run,
                    raw_location_id=raw_location_id,
                    catalogue_entry=catalogue.get(raw_location_id),
                    registry_version=locations.get("registryVersion"),
                    partial=bool(locations.get("partial", False)),
                    first_visit_utc=first_visit.get("utc"),
                    first_visit_world_age_hours=first_visit.get("worldAgeHours"),
                    building_id=str(first_visit.get("buildingId") or ""),
                    point_id=str(first_visit.get("pointId") or ""),
                    discovery_method=str(first_visit.get("discoveryMethod") or ""),
                    x=first_visit.get("x"),
                    y=first_visit.get("y"),
                )
            )
    RunLandmark.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("registry", "0041_runlandmark")]

    operations = [migrations.RunPython(backfill_run_landmarks, migrations.RunPython.noop)]
