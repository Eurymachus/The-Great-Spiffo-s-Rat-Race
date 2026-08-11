from django.core.management.base import BaseCommand, CommandError

from operations.deployment_checks import evaluate_production_deployment_checks


class Command(BaseCommand):
    help = "Validate production configuration and host dependencies."

    def handle(self, *args, **options):
        results = evaluate_production_deployment_checks()
        for name, passed in results.items():
            marker = "PASS" if passed else "FAIL"
            self.stdout.write(f"[{marker}] {name}")

        failed = [name for name, passed in results.items() if not passed]
        if failed:
            raise CommandError(
                "Production deployment check failed: " + ", ".join(failed)
            )

        self.stdout.write(self.style.SUCCESS("Production deployment check passed."))
