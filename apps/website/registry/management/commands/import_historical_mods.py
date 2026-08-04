from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from registry.historical_mods import (
    HISTORICAL_UNSTABLE_MODS,
    HISTORICAL_UNSTABLE_SOURCE,
)
from registry.models import WorkshopMod
from registry.steam_workshop import (
    SteamWorkshopError,
    fetch_project_zomboid_workshop_item,
)


class Command(BaseCommand):
    help = "Import historical Unstable mod rulings and refresh their Steam metadata."

    def handle(self, *args, **options):
        imported = 0
        updated = 0
        failures = []
        for workshop_id, (previous_ruling, note) in HISTORICAL_UNSTABLE_MODS.items():
            try:
                steam_item = fetch_project_zomboid_workshop_item(workshop_id)
            except SteamWorkshopError as exc:
                failures.append(f"{workshop_id}: {exc}")
                continue
            existing = WorkshopMod.objects.filter(workshop_id=workshop_id).first()
            defaults = {
                **steam_item,
                "previous_unstable_ruling": previous_ruling,
                "unstable_ruling_notes": f"{note} {HISTORICAL_UNSTABLE_SOURCE}",
                "steam_checked_at": timezone.now(),
            }
            if existing is None:
                defaults["ruling"] = WorkshopMod.Ruling.PENDING
                WorkshopMod.objects.create(**defaults)
                imported += 1
            else:
                for field, value in defaults.items():
                    setattr(existing, field, value)
                existing.save(update_fields=(*defaults.keys(), "updated_at"))
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Historical mods: {imported} imported, {updated} updated, "
                f"{len(failures)} failed."
            )
        )
        if failures:
            raise CommandError("\n".join(failures))
