import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from zomboid_catalogue.models import CatalogueAlias, CatalogueEntry


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "b42_19.json"


class Command(BaseCommand):
    help = "Import the version-controlled Project Zomboid identifier catalogue."

    def add_arguments(self, parser):
        parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)

    @transaction.atomic
    def handle(self, *args, **options):
        source = options["source"]
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read catalogue {source}: {exc}") from exc
        if document.get("schema_version") != 1:
            raise CommandError("Unsupported catalogue schema_version.")
        game_version = str(document.get("game_version") or "").strip()
        if not game_version:
            raise CommandError("Catalogue game_version is required.")

        valid_kinds = {value for value, _label in CatalogueEntry.Kind.choices}
        created = updated = unchanged = 0
        for index, definition in enumerate(document.get("entries") or [], start=1):
            kind = str(definition.get("kind") or "")
            stable_id = str(definition.get("stable_id") or "").strip()
            display_name = str(definition.get("display_name") or "").strip()
            if kind not in valid_kinds or not stable_id or not display_name:
                raise CommandError(f"Invalid catalogue entry at position {index}.")
            defaults = {
                "display_name": display_name,
                "category": str(definition.get("category") or ""),
                "removed_in": str(definition.get("removed_in") or ""),
                "icon_key": str(definition.get("icon_key") or ""),
                "is_active": bool(definition.get("is_active", True)),
                "notes": str(definition.get("notes") or ""),
            }
            entry, was_created = CatalogueEntry.objects.get_or_create(
                kind=kind,
                stable_id=stable_id,
                introduced_in=str(definition.get("introduced_in") or game_version),
                defaults=defaults,
            )
            if was_created:
                created += 1
            elif any(getattr(entry, field) != value for field, value in defaults.items()):
                for field, value in defaults.items():
                    setattr(entry, field, value)
                entry.full_clean()
                entry.save(update_fields=(*defaults.keys(), "updated_at"))
                updated += 1
            else:
                unchanged += 1
            for alias in definition.get("aliases") or []:
                alias_id = str(alias.get("stable_id") or "").strip()
                if not alias_id:
                    raise CommandError(f"Blank alias on catalogue entry {stable_id}.")
                CatalogueAlias.objects.update_or_create(
                    stable_id=alias_id,
                    introduced_in=str(alias.get("introduced_in") or game_version),
                    defaults={
                        "entry": entry,
                        "removed_in": str(alias.get("removed_in") or ""),
                        "notes": str(alias.get("notes") or ""),
                    },
                )
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue {game_version}: {created} created, "
            f"{updated} updated, {unchanged} unchanged."
        ))
