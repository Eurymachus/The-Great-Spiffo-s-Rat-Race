import hashlib
from pathlib import Path

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from zomboid_catalogue.models import (
    CatalogueAsset,
    CatalogueEntry,
    ItemDisplayCategory,
    ItemDetails,
    OccupationDetails,
    SkillDetails,
    TraitDetails,
)
from zomboid_catalogue.pz_import import PZCatalogueSource

from .models import CatalogueImportReview, ReferenceSource


CATEGORY_SKILLS = {"Agility", "Combat", "Crafting", "FarmingCategory", "Firearm", "PhysicalCategory", "Survivalist"}
DETAIL_MODELS = {
    CatalogueEntry.Kind.TRAIT: TraitDetails,
    CatalogueEntry.Kind.OCCUPATION: OccupationDetails,
    CatalogueEntry.Kind.SKILL: SkillDetails,
    CatalogueEntry.Kind.ITEM: ItemDetails,
}


def build_snapshot(game_root, decompiled_root):
    source = PZCatalogueSource(
        Path(game_root), decompiled_root=Path(decompiled_root)
    )
    records = []
    for definition in source.traits():
        fields = definition.fields
        stable_id = definition.stable_id
        icon_key = f"trait_{stable_id.split(':', 1)[-1].replace(' ', '_')}"
        records.append({
            "kind": CatalogueEntry.Kind.TRAIT, "stable_id": stable_id,
            "display_name": source.display_text(fields.get("UIName", ""), stable_id),
            "icon_key": icon_key,
            "details": {
                "point_cost": int(fields.get("Cost", 0)),
                "description": source.display_text(fields.get("UIDescription", "")),
                "is_profession_trait": source.truthy(fields.get("IsProfessionTrait", "false")),
                "disabled_in_multiplayer": source.truthy(fields.get("DisabledInMultiplayer", "false")),
                "xp_boosts": source.xp_boosts(fields.get("XPBoosts", "")),
                "mutually_exclusive_traits": source.split_values(fields.get("MutuallyExclusiveTraits", "")),
                "granted_recipes": source.split_values(fields.get("GrantedRecipes", "")),
            },
            "asset": _asset_snapshot(icon_key, source.trait_icon(stable_id), True),
        })
    for definition in source.occupations():
        fields = definition.fields
        icon_key = fields.get("IconPathName", "")
        records.append({
            "kind": CatalogueEntry.Kind.OCCUPATION, "stable_id": definition.stable_id,
            "display_name": source.display_text(fields.get("UIName", ""), definition.stable_id),
            "icon_key": icon_key,
            "details": {
                "point_cost": int(fields.get("Cost", 0)),
                "description": source.display_text(fields.get("UIDescription", "")),
                "granted_traits": source.split_values(fields.get("GrantedTraits", "")),
                "xp_boosts": source.xp_boosts(fields.get("XPBoosts", "")),
                "granted_recipes": source.split_values(fields.get("GrantedRecipes", "")),
            },
            "asset": _asset_snapshot(icon_key, None, False) if icon_key else None,
        })
    for skill in source.skills():
        if skill.stable_id in CATEGORY_SKILLS:
            continue
        category = source.skill_name(skill.parent_id) if skill.parent_id and skill.parent_id != "None" else ("Passive" if skill.is_passive else "")
        records.append({
            "kind": CatalogueEntry.Kind.SKILL, "stable_id": skill.stable_id,
            "display_name": source.skill_name(skill.translation_key),
            "icon_key": f"perk_{skill.stable_id}",
            "details": {
                "description": source.skill_description(skill.translation_key),
                "category": category, "level_xp": skill.level_xp,
                "is_passive": skill.is_passive,
            },
            "asset": None,
        })
    for item in source.items():
        fields = item.fields
        icon_key = fields.get("Icon", "")
        try:
            weight = float(fields["Weight"]) if fields.get("Weight") else None
        except ValueError:
            weight = None
        display_category_id = fields.get("DisplayCategory", "")
        records.append({
            "kind": CatalogueEntry.Kind.ITEM,
            "stable_id": item.stable_id,
            "display_name": source.item_name(item.stable_id),
            "icon_key": icon_key,
            "details": {
                "pz_item_type": fields.get("ItemType", ""),
                "display_category_stable_id": display_category_id,
                "display_category_display_name": (
                    source.item_display_category_name(display_category_id)
                    if display_category_id
                    else ""
                ),
                "tags": item.tags,
                "capabilities": item.capabilities,
                "weapon_categories": item.weapon_categories,
                "weapon_skill_stable_id": item.weapon_skill,
                "weight": weight,
                "raw_properties": fields,
            },
            "asset": _asset_snapshot(icon_key, None, False) if icon_key else None,
        })
    return sorted(records, key=lambda row: (row["kind"], row["stable_id"]))


def _asset_snapshot(source_key, source_path, copy_file):
    checksum = hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path else ""
    return {"source_key": source_key, "source_path": str(source_path or ""), "source_checksum": checksum, "copy_file": bool(source_path and copy_file)}


def catalogue_diff(snapshot, game_version):
    desired = {(row["kind"], row["stable_id"]): row for row in snapshot}
    current = {(entry.kind, entry.stable_id): entry for entry in CatalogueEntry.objects.filter(kind__in=DETAIL_MODELS, introduced_in=game_version)}
    result = {"added": [], "changed": [], "removed": []}
    for key, row in desired.items():
        entry = current.get(key)
        summary = {name: row[name] for name in ("kind", "stable_id", "display_name")}
        if not entry:
            result["added"].append(summary)
            continue
        changes = [field for field in ("display_name", "icon_key") if getattr(entry, field) != row[field]]
        details = getattr(entry, f"{row['kind']}_details", None)
        if details is None or _details_changed(row, details):
            changes.append("details")
        if not entry.is_active:
            changes.append("activation")
        if changes:
            result["changed"].append({**summary, "fields": changes})
    for key, entry in current.items():
        if key not in desired and entry.is_active:
            result["removed"].append({"kind": entry.kind, "stable_id": entry.stable_id, "display_name": entry.display_name})
    return result


def generate_catalogue_review(review):
    review.started_at = timezone.now()
    review.status = CatalogueImportReview.Status.GENERATING
    review.save(update_fields=("started_at", "status"))
    try:
        review.snapshot = build_snapshot(review.install_root, review.decompiled_root)
        review.diff = catalogue_diff(review.snapshot, review.game_version)
        counts = {key: len(value) for key, value in review.diff.items()}
        review.summary = f"{len(review.snapshot)} records parsed: {counts['added']} additions, {counts['changed']} changes and {counts['removed']} deactivations."
        review.status = CatalogueImportReview.Status.READY
    except Exception as exc:
        review.status = CatalogueImportReview.Status.FAILED
        review.summary = f"Catalogue review failed: {exc}"
    review.finished_at = timezone.now()
    review.save(update_fields=("snapshot", "diff", "summary", "status", "finished_at"))


@transaction.atomic
def approve_catalogue_review(review, reviewer):
    from .models import PZWikiArtworkSyncJob
    from .pzwiki_artwork import enqueue_pzwiki_artwork_sync

    review = CatalogueImportReview.objects.select_for_update().select_related("source").get(pk=review.pk)
    source = ReferenceSource.objects.select_for_update().get(pk=review.source_id)
    if review.status != CatalogueImportReview.Status.READY:
        raise ValueError("Only a ready catalogue review can be approved.")
    if (source.installed_build_id, source.decompiled_build_id, source.install_root, source.decompiled_root) != (review.installed_build_id, review.decompiled_build_id, review.install_root, review.decompiled_root):
        review.status = CatalogueImportReview.Status.STALE
        review.summary += " Approval blocked because the reference source changed."
        review.save(update_fields=("status", "summary"))
        return review
    desired_keys = set()
    for row in _dependency_order(review.snapshot):
        desired_keys.add((row["kind"], row["stable_id"]))
        entry, _ = CatalogueEntry.objects.get_or_create(
            kind=row["kind"], stable_id=row["stable_id"], introduced_in=review.game_version,
            defaults={"display_name": row["display_name"], "icon_key": row["icon_key"]},
        )
        entry.display_name, entry.icon_key = row["display_name"], row["icon_key"]
        entry.is_active, entry.removed_in = True, ""
        entry.full_clean()
        entry.save()
        DETAIL_MODELS[row["kind"]].objects.update_or_create(
            entry=entry,
            defaults=_detail_defaults(row),
        )
        if row["asset"]:
            _apply_asset(entry, row["asset"])
    for entry in CatalogueEntry.objects.filter(kind__in=DETAIL_MODELS, introduced_in=review.game_version, is_active=True):
        if (entry.kind, entry.stable_id) not in desired_keys:
            entry.is_active = False
            entry.save(update_fields=("is_active", "updated_at"))
    _delete_unused_item_categories()
    review.status = CatalogueImportReview.Status.APPROVED
    review.reviewed_by = reviewer
    review.reviewed_at = timezone.now()
    review.save(update_fields=("status", "reviewed_by", "reviewed_at"))
    enqueue_pzwiki_artwork_sync(
        catalogue_review=review,
        trigger=PZWikiArtworkSyncJob.Trigger.CATALOGUE_APPROVAL,
        requested_by=reviewer,
    )
    return review


@transaction.atomic
def revert_catalogue_review(review, reviewer):
    from .models import PZWikiArtworkSyncJob

    review = CatalogueImportReview.objects.select_for_update().get(pk=review.pk)
    if review.status != CatalogueImportReview.Status.APPROVED:
        raise ValueError("Only an approved catalogue review can be reverted.")
    baseline = (
        CatalogueImportReview.objects.select_for_update()
        .filter(
            source_id=review.source_id,
            game_version=review.game_version,
            status=CatalogueImportReview.Status.APPROVED,
            reviewed_at__lt=review.reviewed_at,
        )
        .order_by("-reviewed_at", "-pk")
        .first()
    )
    if baseline is None:
        raise ValueError("No earlier approved catalogue snapshot is available.")

    baseline_keys = {
        (row["kind"], row["stable_id"]) for row in baseline.snapshot
    }
    review_keys = {(row["kind"], row["stable_id"]) for row in review.snapshot}
    removed_keys = sorted(
        review_keys - baseline_keys,
        key=lambda key: (key[0] != CatalogueEntry.Kind.ITEM, key),
    )
    for kind, stable_id in removed_keys:
        CatalogueEntry.objects.filter(
            kind=kind,
            stable_id=stable_id,
            introduced_in=review.game_version,
        ).delete()

    for row in _dependency_order(baseline.snapshot):
        entry, _ = CatalogueEntry.objects.get_or_create(
            kind=row["kind"],
            stable_id=row["stable_id"],
            introduced_in=baseline.game_version,
            defaults={
                "display_name": row["display_name"],
                "icon_key": row["icon_key"],
            },
        )
        entry.display_name = row["display_name"]
        entry.icon_key = row["icon_key"]
        entry.is_active = True
        entry.removed_in = ""
        entry.full_clean()
        entry.save()
        DETAIL_MODELS[row["kind"]].objects.update_or_create(
            entry=entry,
            defaults=_detail_defaults(row),
        )
        if row["asset"]:
            _apply_asset(entry, row["asset"])
    _delete_unused_item_categories()

    review.status = CatalogueImportReview.Status.REVERTED
    review.summary = (
        f"{review.summary} Reverted to approved catalogue review "
        f"#{baseline.pk} by {reviewer}."
    ).strip()
    review.save(update_fields=("status", "summary"))
    PZWikiArtworkSyncJob.objects.filter(
        catalogue_review=review,
        status=PZWikiArtworkSyncJob.Status.QUEUED,
    ).update(
        status=PZWikiArtworkSyncJob.Status.CANCELLED,
        finished_at=timezone.now(),
        summary="Cancelled because the catalogue approval was reverted.",
    )
    return review


def _dependency_order(snapshot):
    return sorted(
        snapshot,
        key=lambda row: (
            row["kind"] == CatalogueEntry.Kind.ITEM,
            row["kind"],
            row["stable_id"],
        ),
    )


def _delete_unused_item_categories():
    ItemDisplayCategory.objects.filter(items__isnull=True).delete()


def _details_changed(row, details):
    expected = row["details"]
    if row["kind"] != CatalogueEntry.Kind.ITEM:
        return any(getattr(details, field) != value for field, value in expected.items())
    scalar_fields = {
        key: value
        for key, value in expected.items()
        if key
        not in {
            "display_category_stable_id",
            "display_category_display_name",
            "weapon_skill_stable_id",
        }
    }
    if any(getattr(details, field) != value for field, value in scalar_fields.items()):
        return True
    actual_category = (
        details.display_category.stable_id if details.display_category_id else ""
    )
    actual_skill = (
        details.weapon_skill.entry.stable_id if details.weapon_skill_id else ""
    )
    return (
        actual_category != expected["display_category_stable_id"]
        or actual_skill != expected["weapon_skill_stable_id"]
    )


def _detail_defaults(row):
    details = dict(row["details"])
    if row["kind"] != CatalogueEntry.Kind.ITEM:
        return details
    category_id = details.pop("display_category_stable_id")
    category_name = details.pop("display_category_display_name")
    skill_id = details.pop("weapon_skill_stable_id")
    details["display_category"] = None
    if category_id:
        details["display_category"], _ = ItemDisplayCategory.objects.update_or_create(
            stable_id=category_id,
            defaults={"display_name": category_name or category_id},
        )
    details["weapon_skill"] = (
        SkillDetails.objects.filter(entry__stable_id=skill_id).first()
        if skill_id
        else None
    )
    return details


def _apply_asset(entry, data):
    asset, _ = CatalogueAsset.objects.get_or_create(
        entry=entry,
        role=CatalogueAsset.Role.ICON,
        source_key=data["source_key"],
        defaults={"alt_text": entry.display_name},
    )
    path = Path(data["source_path"]) if data["source_path"] else None
    if (
        path
        and data["source_checksum"]
        and hashlib.sha256(path.read_bytes()).hexdigest() != data["source_checksum"]
    ):
        raise ValueError(f"Reviewed asset changed: {path}")

    asset.alt_text = entry.display_name
    if not data["copy_file"]:
        asset.game_availability = CatalogueAsset.GameAvailability.PACKED
        asset.game_source_path = ""
        asset.game_source_checksum = ""
        if not asset.file:
            asset.source_type = CatalogueAsset.SourceType.UNKNOWN
            asset.source_path = ""
            asset.source_checksum = ""
            asset.availability = CatalogueAsset.Availability.PACKED
        asset.save()
        return

    asset.game_availability = CatalogueAsset.GameAvailability.UNPACKED
    asset.game_source_path = str(path or "")
    asset.game_source_checksum = data["source_checksum"]
    if asset.source_type in (
        CatalogueAsset.SourceType.MANUAL,
        CatalogueAsset.SourceType.PZWIKI,
    ) and asset.file:
        asset.save()
        return

    previous_checksum = asset.source_checksum
    asset.source_type = CatalogueAsset.SourceType.GAME
    asset.source_path = str(path or "")
    asset.source_checksum = data["source_checksum"]
    asset.availability = CatalogueAsset.Availability.IMPORTED
    if path and (not asset.file or previous_checksum != data["source_checksum"]):
        with path.open("rb") as handle:
            asset.file.save(path.name, File(handle), save=False)
    asset.save()
