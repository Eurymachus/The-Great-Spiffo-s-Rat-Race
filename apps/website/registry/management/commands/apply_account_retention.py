from django.core.management.base import BaseCommand, CommandError

from registry.models import RetentionFileDeletion
from registry.retention import (
    AccountDeletionBlocked, delete_overdue_registration, deletion_blockers,
    drain_file_deletions, overdue_registrations,
)


class Command(BaseCommand):
    help = "Preview account retention; --apply deletes unverified accounts after 30 days and retries queued file cleanup."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        candidates = list(overdue_registrations().order_by("pk"))
        eligible = blocked = deleted = 0
        for participant in candidates:
            if deletion_blockers(participant):
                blocked += 1
                continue
            eligible += 1
            if options["apply"]:
                try:
                    deleted += int(delete_overdue_registration(participant.pk))
                except AccountDeletionBlocked:
                    blocked += 1
        self.stdout.write(f"Candidates: {len(candidates)}; eligible: {eligible}; blocked: {blocked}; deleted: {deleted}.")
        if options["apply"]:
            files, failed = drain_file_deletions()
            self.stdout.write(f"Files deleted: {files}; file jobs requiring retry: {failed}.")
            if blocked or failed:
                raise CommandError("Retention needs administrator review. No personal identifiers were logged.")
        else:
            self.stdout.write(f"Preview only. Pending file deletions: {RetentionFileDeletion.objects.count()}.")
