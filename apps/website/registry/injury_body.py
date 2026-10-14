from zomboid_catalogue.models import CatalogueAsset
from zomboid_catalogue.management.commands.import_health_body_artwork import PARTS


def injury_body_data(run, projection):
    assets = CatalogueAsset.objects.filter(entry__kind="body_part",
        availability="imported").exclude(file="").select_related("entry").order_by("entry__introduced_in", "pk")
    views = {"male": {}, "female": {}}
    for asset in assets:
        sex, _, part = asset.entry.stable_id.partition(":")
        if sex in views:
            views[sex][part] = asset.file.url
    if not all("body" in view and all(part in view for part in PARTS) for view in views.values()):
        return None
    summary = run.statistic_summaries.filter(kind="injuries").first()
    totals, pairs = {}, {}
    if summary:
        for metric in summary.metrics.all():
            if metric.dimension == "body_part":
                totals[metric.raw_primary_id] = metric.value
            elif metric.dimension == "injury_pair":
                pairs.setdefault(metric.raw_secondary_id, []).append({"name": metric.raw_primary_id.replace("_", " ").capitalize(), "count": metric.value})
    else:
        source = (projection.get("injuries") or {}).get("all") or {}
        totals = {row["id"]: row["count"] for row in source.get("byBodyPart", [])}
        for row in source.get("pairs", []):
            pairs.setdefault(row["bodyPart"], []).append({"name": row["injuryType"].replace("_", " ").capitalize(), "count": row["count"]})
    parts = []
    for identifier, filename in PARTS.items():
        injuries = sorted(pairs.get(identifier, []), key=lambda row: (-row["count"], row["name"]))
        paired = sum(row["count"] for row in injuries)
        total = totals.get(identifier, paired)
        parts.append({"id": identifier, "name": filename.replace("-", " ").capitalize(),
                      "total": total, "injuries": injuries, "unclassified": max(0, total-paired)})
    character = getattr(run, "character_record", None)
    sex = (character.current_sex or character.starting_sex) if character else ""
    return {"sex": sex, "views": views, "parts": parts,
            "unmapped": [{"name": key, "count": value} for key, value in totals.items() if key not in PARTS and value > 0]}
