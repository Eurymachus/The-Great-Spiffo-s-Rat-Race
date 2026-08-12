import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, UnidentifiedImageError

from zomboid_catalogue.models import CatalogueAsset, CatalogueEntry


DEFAULT_PACK_PATH = (
    Path(settings.BASE_DIR).parents[1] / "deployment" / "assets" / "skill-icons"
)


class Command(BaseCommand):
    help = "Install the version-controlled Project Zomboid skill icon pack."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pack-path",
            type=Path,
            default=DEFAULT_PACK_PATH,
            help="Directory containing manifest.json and the skill icon PNG files.",
        )

    def handle(self, *args, **options):
        pack_path = Path(options["pack_path"]).resolve()
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.is_file():
            raise CommandError(f"Skill icon manifest not found: {manifest_path}")

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Unable to read skill icon manifest: {exc}") from exc

        entries = manifest.get("entries")
        if manifest.get("version") != 1 or not isinstance(entries, list):
            raise CommandError("The skill icon manifest must use version 1 and an entries list.")

        stable_ids = []
        filenames = []
        prepared = []
        for item in entries:
            if not isinstance(item, dict):
                raise CommandError("Every skill icon manifest entry must be an object.")
            stable_id = str(item.get("stable_id") or "").strip()
            filename = str(item.get("filename") or "").strip()
            if not stable_id or not filename:
                raise CommandError("Every skill icon requires a stable_id and filename.")
            if Path(filename).name != filename or not filename.lower().endswith(".png"):
                raise CommandError(f"Invalid skill icon filename: {filename}")
            stable_ids.append(stable_id)
            filenames.append(filename.casefold())

            source_file = pack_path / filename
            if not source_file.is_file():
                raise CommandError(f"Skill icon file not found: {source_file}")
            try:
                with Image.open(source_file) as image:
                    image.verify()
            except (OSError, UnidentifiedImageError) as exc:
                raise CommandError(f"Invalid skill icon image {source_file}: {exc}") from exc
            payload = source_file.read_bytes()
            prepared.append(
                (stable_id, filename, payload, hashlib.sha256(payload).hexdigest())
            )

        if len(stable_ids) != len(set(stable_ids)):
            raise CommandError("The skill icon manifest contains duplicate stable IDs.")
        if len(filenames) != len(set(filenames)):
            raise CommandError("The skill icon manifest contains duplicate filenames.")

        catalogue = {
            entry.stable_id: entry
            for entry in CatalogueEntry.objects.filter(
                kind=CatalogueEntry.Kind.SKILL,
                stable_id__in=stable_ids,
                is_active=True,
            )
        }
        missing = sorted(set(stable_ids) - set(catalogue))
        if missing:
            raise CommandError(
                "The catalogue is missing active skills required by the icon pack: "
                + ", ".join(missing)
            )

        installed = 0
        unchanged = 0
        source_root = "deployment/assets/skill-icons"
        for stable_id, filename, payload, checksum in prepared:
            entry = catalogue[stable_id]
            canonical_icon_key = f"perk_{stable_id}"
            if entry.icon_key != canonical_icon_key:
                entry.icon_key = canonical_icon_key
                entry.save(update_fields=("icon_key", "updated_at"))
            asset, _created = CatalogueAsset.objects.get_or_create(
                entry=entry,
                role=CatalogueAsset.Role.ICON,
                source_key=canonical_icon_key,
            )
            if (
                asset.source_type == CatalogueAsset.SourceType.MANUAL
                and asset.source_checksum == checksum
                and asset.file
                and asset.file.storage.exists(asset.file.name)
            ):
                unchanged += 1
                continue

            if asset.file:
                asset.file.delete(save=False)
            asset.file.save(filename, ContentFile(payload), save=False)
            asset.source_path = f"{source_root}/{filename}"
            asset.source_checksum = checksum
            asset.source_type = CatalogueAsset.SourceType.MANUAL
            asset.game_availability = CatalogueAsset.GameAvailability.UNKNOWN
            asset.game_source_path = ""
            asset.game_source_checksum = ""
            asset.availability = CatalogueAsset.Availability.IMPORTED
            asset.alt_text = f"{entry.display_name} skill icon"
            asset.caption = ""
            asset.save()
            installed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Skill icon pack ready: {installed} installed, {unchanged} unchanged."
            )
        )
