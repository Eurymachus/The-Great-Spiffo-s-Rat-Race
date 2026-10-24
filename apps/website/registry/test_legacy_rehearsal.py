from io import StringIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from .legacy_imports import apply_legacy_import, create_legacy_import_review
from .models import (
    ChallengeRun, LegacyDataImport, LegacyRun, LegacyRunClaim,
    LegacyRunSubmission, Notification, Participant, RunSubmission, StreamingAccount,
)


@override_settings(STAGING_ENVIRONMENT=True)
class LegacyRehearsalTests(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create_user(
            email="rehearsal@example.com", nickname="Rehearsal", password="test-password",
        )
        self.import_data()
        run = LegacyRun.objects.get()
        run.claimed_participant = self.participant
        run.save()
        for status in LegacyRunClaim.Status.values:
            claimant = Participant.objects.create_user(
                email=f"{status}@example.com", nickname=status, password="test-password",
            )
            LegacyRunClaim.objects.create(run=run, participant=claimant, status=status)
        LegacyRunSubmission.objects.create(
            run=run, source=LegacyRunSubmission.Source.PARTICIPANT,
            submitted_by=self.participant,
        )
        for provider in ("twitch", "youtube"):
            StreamingAccount.objects.create(
                participant=self.participant, provider=provider,
                provider_identity=provider, channel_identity=provider,
                encrypted_access_token="stored-access", encrypted_refresh_token="stored-refresh",
            )
        self.participant.primary_streaming_account = StreamingAccount.objects.first()
        self.participant.save()
        current_run = ChallengeRun.objects.create(
            participant=self.participant, run_id="preserved-run", export_format=3,
            generated_at=timezone.now(), event_hash="a" * 64,
        )
        submission = RunSubmission.objects.create(
            run=current_run, submitter=self.participant, checksum="b" * 64,
            raw_export="immutable-evidence", export_format=3,
            generated_at=timezone.now(), event_hash="a" * 64,
        )
        current_run.approved_submission = submission
        current_run.save()
        Notification.objects.create(recipient=self.participant, title="Rehearsal", message="Retained")

    def import_data(self):
        csv = (
            "Position,Name,Zombies Killed,Survival Time (Full),Survival Time (Days),"
            "Kills / Day Average,Playtime Approximation,Outposts Cleared,Level 10 Skills,"
            "Overall Challenge Progress,Source\n"
            "1,Rehearsal,100,,12,0,0,2,3,10.5,\n"
        ).encode()
        review = create_legacy_import_review(
            leaderboard_upload=SimpleUploadedFile("leaderboard.csv", csv),
            hall_of_fame_upload=SimpleUploadedFile("hall.csv", csv),
            uploaded_by=self.participant,
        )
        apply_legacy_import(review, self.participant)

    def reset(self, **options):
        output = StringIO()
        call_command("reset_legacy_rehearsal", stdout=output, **options)
        return output.getvalue()

    def test_preview_does_not_change_data(self):
        before = self.snapshot()
        self.assertIn("Preview only", self.reset())
        self.assertEqual(self.snapshot(), before)

    def snapshot(self):
        return {
            model.__name__: list(model.objects.order_by("pk").values())
            for model in (Participant, StreamingAccount, ChallengeRun, RunSubmission,
                          Notification, LegacyDataImport, LegacyRun, LegacyRunClaim,
                          LegacyRunSubmission)
        }

    def test_reset_preserves_other_data_and_allows_repeated_import(self):
        before = self.snapshot()
        self.reset(confirm=True)
        after = self.snapshot()
        for name, rows in before.items():
            self.assertEqual(after[name], [] if name in {
                "LegacyRun", "LegacyRunClaim", "LegacyRunSubmission",
            } else rows)
        self.reset(confirm=True)
        self.import_data()
        self.assertEqual(LegacyRun.objects.count(), 1)
        self.assertEqual(LegacyDataImport.objects.count(), 2)

    def test_non_staging_refused_even_with_confirmation(self):
        before = self.snapshot()
        for setting in (False, "true", None):
            with self.subTest(setting=setting), override_settings(STAGING_ENVIRONMENT=setting):
                for confirm in (False, True):
                    with self.assertRaisesMessage(CommandError, "restricted to staging"):
                        self.reset(confirm=confirm)
        self.assertEqual(self.snapshot(), before)

    def test_failure_rolls_back_deletion(self):
        from django.db.models.query import QuerySet

        original_delete = QuerySet.delete

        def fail_after_delete(queryset):
            original_delete(queryset)
            raise RuntimeError("simulated failure")

        before = self.snapshot()
        with patch.object(QuerySet, "delete", fail_after_delete):
            with self.assertRaisesMessage(RuntimeError, "simulated failure"):
                self.reset(confirm=True)
        self.assertEqual(self.snapshot(), before)
