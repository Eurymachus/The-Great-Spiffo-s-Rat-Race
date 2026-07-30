import hashlib
import os
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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


DEFAULT_GAME_ROOT = Path(
    os.environ.get(
        "PZ_GAME_ROOT",
        r"C:\Games\Steam\steamapps\common\ProjectZomboid",
    )
)
CATEGORY_SKILLS = {
    "Agility",
    "Combat",
    "Crafting",
    "FarmingCategory",
    "Firearm",
    "PhysicalCategory",
    "Survivalist",
}


class Command(BaseCommand):
    help = "Import typed catalogue records directly from an installed Project Zomboid build."

    def add_arguments(self, parser):
        parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
        parser.add_argument("--decompiled-root", type=Path)
        parser.add_argument("--game-version", required=True)
        parser.add_argument(
            "--no-assets",
            action="store_true",
            help="Record texture keys without copying available loose image files.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        game_version = str(options["game_version"]).strip()
        if not game_version:
            raise CommandError("--game-version cannot be blank.")
        try:
            source = PZCatalogueSource(
                options["game_root"],
                decompiled_root=options["decompiled_root"],
            )
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        counters = {"created": 0, "updated": 0, "unchanged": 0}
        for definition in source.traits():
            fields = definition.fields
            entry = self._entry(
                counters,
                kind=CatalogueEntry.Kind.TRAIT,
                stable_id=definition.stable_id,
                game_version=game_version,
                display_name=source.display_text(
                    fields.get("UIName", ""), definition.stable_id
                ),
                icon_key=f"trait_{definition.stable_id.split(':', 1)[-1].replace(' ', '_')}",
            )
            TraitDetails.objects.update_or_create(
                entry=entry,
                defaults={
                    "point_cost": int(fields.get("Cost", 0)),
                    "description": source.display_text(fields.get("UIDescription", "")),
                    "is_profession_trait": source.truthy(
                        fields.get("IsProfessionTrait", "false")
                    ),
                    "disabled_in_multiplayer": source.truthy(
                        fields.get("DisabledInMultiplayer", "false")
                    ),
                    "xp_boosts": source.xp_boosts(fields.get("XPBoosts", "")),
                    "mutually_exclusive_traits": source.split_values(
                        fields.get("MutuallyExclusiveTraits", "")
                    ),
                    "granted_recipes": source.split_values(
                        fields.get("GrantedRecipes", "")
                    ),
                },
            )
            self._asset(
                entry,
                source.trait_icon(definition.stable_id),
                entry.icon_key,
                copy_file=not options["no_assets"],
            )

        for definition in source.occupations():
            fields = definition.fields
            icon_key = fields.get("IconPathName", "")
            entry = self._entry(
                counters,
                kind=CatalogueEntry.Kind.OCCUPATION,
                stable_id=definition.stable_id,
                game_version=game_version,
                display_name=source.display_text(
                    fields.get("UIName", ""), definition.stable_id
                ),
                icon_key=icon_key,
            )
            OccupationDetails.objects.update_or_create(
                entry=entry,
                defaults={
                    "point_cost": int(fields.get("Cost", 0)),
                    "description": source.display_text(fields.get("UIDescription", "")),
                    "granted_traits": source.split_values(
                        fields.get("GrantedTraits", "")
                    ),
                    "xp_boosts": source.xp_boosts(fields.get("XPBoosts", "")),
                    "granted_recipes": source.split_values(
                        fields.get("GrantedRecipes", "")
                    ),
                },
            )
            if icon_key:
                self._asset(entry, None, icon_key, copy_file=False)

        for skill in source.skills():
            if skill.stable_id in CATEGORY_SKILLS:
                continue
            category = (
                source.skill_name(skill.parent_id)
                if skill.parent_id and skill.parent_id != "None"
                else ("Passive" if skill.is_passive else "")
            )
            entry = self._entry(
                counters,
                kind=CatalogueEntry.Kind.SKILL,
                stable_id=skill.stable_id,
                game_version=game_version,
                display_name=source.skill_name(skill.translation_key),
                icon_key=f"perk_{skill.stable_id}",
            )
            SkillDetails.objects.update_or_create(
                entry=entry,
                defaults={
                    "description": source.skill_description(skill.translation_key),
                    "category": category,
                    "level_xp": skill.level_xp,
                    "is_passive": skill.is_passive,
                },
            )

        for item in source.items():
            fields = item.fields
            icon_key = fields.get("Icon", "")
            entry = self._entry(
                counters,
                kind=CatalogueEntry.Kind.ITEM,
                stable_id=item.stable_id,
                game_version=game_version,
                display_name=source.item_name(item.stable_id),
                icon_key=icon_key,
            )
            try:
                weight = float(fields["Weight"]) if fields.get("Weight") else None
            except ValueError:
                weight = None
            display_category_id = fields.get("DisplayCategory", "")
            display_category = None
            if display_category_id:
                display_category, _ = ItemDisplayCategory.objects.update_or_create(
                    stable_id=display_category_id,
                    defaults={
                        "display_name": source.item_display_category_name(
                            display_category_id
                        )
                    },
                )
            weapon_skill = (
                SkillDetails.objects.filter(entry__stable_id=item.weapon_skill).first()
                if item.weapon_skill
                else None
            )
            ItemDetails.objects.update_or_create(
                entry=entry,
                defaults={
                    "pz_item_type": fields.get("ItemType", ""),
                    "display_category": display_category,
                    "tags": item.tags,
                    "capabilities": item.capabilities,
                    "weapon_categories": item.weapon_categories,
                    "weapon_skill": weapon_skill,
                    "weight": weight,
                    "raw_properties": fields,
                },
            )
            if icon_key:
                self._asset(entry, None, icon_key, copy_file=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Project Zomboid {game_version}: {counters['created']} created, "
                f"{counters['updated']} updated, {counters['unchanged']} unchanged."
            )
        )

    @staticmethod
    def _entry(counters, *, kind, stable_id, game_version, **defaults):
        entry, created = CatalogueEntry.objects.get_or_create(
            kind=kind,
            stable_id=stable_id,
            introduced_in=game_version,
            defaults=defaults,
        )
        if created:
            counters["created"] += 1
            return entry
        changed = False
        for field, value in defaults.items():
            if getattr(entry, field) != value:
                setattr(entry, field, value)
                changed = True
        if changed:
            entry.full_clean()
            entry.save(update_fields=(*defaults.keys(), "updated_at"))
            counters["updated"] += 1
        else:
            counters["unchanged"] += 1
        return entry

    @staticmethod
    def _asset(entry, source_path, source_key, *, copy_file):
        checksum = ""
        if source_path:
            checksum = hashlib.sha256(source_path.read_bytes()).hexdigest()
        asset, _created = CatalogueAsset.objects.get_or_create(
            entry=entry,
            role=CatalogueAsset.Role.ICON,
            source_key=source_key,
            defaults={"alt_text": entry.display_name},
        )
        asset.alt_text = entry.display_name
        if not copy_file:
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
        asset.game_source_path = str(source_path or "")
        asset.game_source_checksum = checksum
        if asset.source_type in (
            CatalogueAsset.SourceType.MANUAL,
            CatalogueAsset.SourceType.PZWIKI,
        ) and asset.file:
            asset.save()
            return

        previous_checksum = asset.source_checksum
        asset.source_type = CatalogueAsset.SourceType.GAME
        asset.source_path = str(source_path or "")
        asset.source_checksum = checksum
        asset.availability = CatalogueAsset.Availability.IMPORTED
        if source_path and (not asset.file or previous_checksum != checksum):
            with source_path.open("rb") as handle:
                asset.file.save(source_path.name, File(handle), save=False)
        asset.save()
