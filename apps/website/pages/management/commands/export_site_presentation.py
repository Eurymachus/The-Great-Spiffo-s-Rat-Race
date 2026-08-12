from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from pages.site_presentation import export_presentation


DEFAULT_PATH = Path(settings.BASE_DIR).parents[1] / "deployment" / "site-presentation"


class Command(BaseCommand):
    help = "Export the approved database-authored public presentation for deployment."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=DEFAULT_PATH)

    def handle(self, *args, **options):
        presentation = export_presentation(options["output"])
        self.stdout.write(self.style.SUCCESS(
            "Presentation exported: "
            f"{len(presentation['pages'])} pages, "
            f"{len(presentation['managed_images'])} images."
        ))
