from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pages.site_presentation import PresentationPackageError, import_presentation


DEFAULT_PATH = Path(settings.BASE_DIR).parents[1] / "deployment" / "site-presentation"


class Command(BaseCommand):
    help = "Validate and transactionally install the public presentation package."

    def add_arguments(self, parser):
        parser.add_argument("--package", type=Path, default=DEFAULT_PATH)

    def handle(self, *args, **options):
        try:
            presentation = import_presentation(options["package"])
        except PresentationPackageError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            "Presentation imported: "
            f"{len(presentation['pages'])} pages, "
            f"{len(presentation['managed_images'])} images."
        ))
