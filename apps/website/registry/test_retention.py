import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AccountClosureRecord, LegacyRun, LegacyRunClaim, Notification, Participant,
    ParticipantSavedView, RetentionFileDeletion, StreamingAccount, WorkshopMod,
)
from .retention import (
    AccountDeletionBlocked, close_account, delete_overdue_registration,
    deletion_blockers, drain_file_deletions,
)


class AccountRetentionTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.temp.name,
            AVATAR_QUARANTINE_ROOT=str(Path(self.temp.name) / "quarantine"),
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def participant(self, name="leaving", **fields):
        return Participant.objects.create_user(
            email=f"{name}@example.test", nickname=name, password="test-password",
            deletion_requested_at=timezone.now(), **fields,
        )

    def age(self, participant, days):
        Participant.objects.filter(pk=participant.pk).update(
            registered_at=timezone.now() - timedelta(days=days),
            verification_sent_at=timezone.now(),
        )

    def test_clean_closure_removes_identity_provider_data_and_private_views(self):
        participant = self.participant()
        StreamingAccount.objects.create(participant=participant, provider="twitch", provider_identity="test")
        Notification.objects.create(recipient=participant, title="Private notification")
        ParticipantSavedView.objects.create(owner=participant, name="Personal", filters={"email": participant.email})
        reference = close_account(participant.pk)
        self.assertFalse(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(StreamingAccount.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(ParticipantSavedView.objects.filter(name="Personal").exists())
        self.assertTrue(AccountClosureRecord.objects.filter(reference=reference).exists())

    def test_closure_with_legacy_history_keeps_identity_and_ownership_intact(self):
        participant = self.participant()
        run = LegacyRun.objects.create(source_key="legacy", normalized_legacy_name="historic", legacy_participant_name="Historic", claimed_participant=participant)
        claim = LegacyRunClaim.objects.create(run=run, participant=participant, status="approved", evidence="Evidence")
        with self.assertRaises(AccountDeletionBlocked):
            close_account(participant.pk)
        run.refresh_from_db()
        self.assertEqual(run.claimed_participant_id, participant.pk)
        self.assertTrue(LegacyRunClaim.objects.filter(pk=claim.pk).exists())
        self.assertFalse(AccountClosureRecord.objects.exists())

    def test_workshop_evidence_requires_review(self):
        participant = self.participant()
        WorkshopMod.objects.create(workshop_id="123", title="Test mod", submitted_by=participant, submission_reason="Private evidence")
        with self.assertRaises(AccountDeletionBlocked):
            close_account(participant.pk)
        self.assertEqual(WorkshopMod.objects.get(workshop_id="123").submission_reason, "Private evidence")

    def test_shared_views_are_not_silently_orphaned(self):
        participant = self.participant()
        ParticipantSavedView.objects.create(owner=participant, name="Team", shared=True)
        self.assertTrue(deletion_blockers(participant))

    def test_hold_blocks_instance_and_bulk_deletion(self):
        participant = self.participant(retention_hold=True)
        for deletion in (participant.delete, lambda: Participant.objects.filter(pk=participant.pk).delete()):
            with self.assertRaises(AccountDeletionBlocked):
                with transaction.atomic():
                    deletion()
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())

    def test_missing_request_and_staff_are_not_closed(self):
        participant = self.participant(is_staff=True)
        with self.assertRaises(AccountDeletionBlocked):
            close_account(participant.pk)
        Participant.objects.filter(pk=participant.pk).update(is_staff=False, deletion_requested_at=None)
        with self.assertRaises(AccountDeletionBlocked):
            close_account(participant.pk)

    def test_retention_preview_is_read_only_and_resend_does_not_extend_deadline(self):
        participant = self.participant()
        self.age(participant, 31)
        output = StringIO()
        call_command("apply_account_retention", stdout=output)
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())
        self.assertIn("eligible: 1", output.getvalue())
        call_command("apply_account_retention", apply=True, stdout=StringIO())
        self.assertFalse(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(AccountClosureRecord.objects.exists())

    def test_cutoff_includes_exactly_thirty_days(self):
        participant = self.participant(status=Participant.Status.EXPIRED)
        now = timezone.now()
        Participant.objects.filter(pk=participant.pk).update(registered_at=now - timedelta(days=30))
        self.assertTrue(delete_overdue_registration(participant.pk, now))

    def test_recent_verified_disabled_and_staff_accounts_survive(self):
        recent = self.participant("recent")
        for name, fields in (
            ("verified", {"status": "verified"}),
            ("timestamp", {"verified_at": timezone.now()}),
            ("disabled", {"status": "disabled"}),
            ("staff", {"is_staff": True}),
            ("superuser", {"is_superuser": True}),
        ):
            participant = self.participant(name, **fields)
            self.age(participant, 31)
        call_command("apply_account_retention", apply=True, stdout=StringIO())
        self.assertEqual(Participant.objects.count(), 6)
        self.assertTrue(Participant.objects.filter(pk=recent.pk).exists())

    def test_held_registration_is_preserved_and_command_reports_attention(self):
        participant = self.participant(retention_hold=True)
        self.age(participant, 31)
        with self.assertRaises(CommandError):
            call_command("apply_account_retention", apply=True, stdout=StringIO())
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())

    def test_verified_between_preview_and_delete_is_preserved(self):
        participant = self.participant()
        self.age(participant, 31)
        Participant.objects.filter(pk=participant.pk).update(status="verified", verified_at=timezone.now())
        self.assertFalse(delete_overdue_registration(participant.pk))

    def test_rollback_keeps_files_and_removes_cleanup_jobs(self):
        participant = self.participant()
        participant.avatar.save("test.webp", ContentFile(b"test"))
        avatar_path = Path(participant.avatar.path)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                close_account(participant.pk)
                raise RuntimeError("Abort transaction")
        self.assertTrue(avatar_path.exists())
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(RetentionFileDeletion.objects.exists())

    def test_file_cleanup_failure_is_retryable(self):
        participant = self.participant()
        participant.avatar.save("test.webp", ContentFile(b"test"))
        avatar_path = Path(participant.avatar.path)
        close_account(participant.pk)
        self.assertTrue(avatar_path.exists())
        with patch.object(Participant._meta.get_field("avatar").storage, "delete", side_effect=OSError):
            self.assertEqual(drain_file_deletions(), (0, 1))
        self.assertTrue(RetentionFileDeletion.objects.exists())
        self.assertEqual(drain_file_deletions(), (1, 0))
        self.assertFalse(avatar_path.exists())

    def test_quarantine_cleanup_rejects_escape_and_preserves_other_files(self):
        root = Path(self.temp.name) / "quarantine"
        root.mkdir()
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("keep")
        RetentionFileDeletion.objects.create(kind="quarantine", name="../outside.txt")
        self.assertEqual(drain_file_deletions(), (0, 1))
        self.assertTrue(outside.exists())

    def test_bulk_delete_queues_avatar_cleanup(self):
        participant = self.participant()
        participant.avatar.save("bulk.webp", ContentFile(b"test"))
        Participant.objects.filter(pk=participant.pk).delete()
        self.assertEqual(RetentionFileDeletion.objects.count(), 1)

    def test_admin_confirmation_explains_blocked_closure(self):
        participant = self.participant(retention_hold=True)
        administrator = Participant.objects.create_superuser(email="admin@example.test", nickname="Admin", password="test-password")
        self.client.force_login(administrator)
        response = self.client.post(reverse("admin:registry_participant_changelist"), {
            "action": "process_account_closures", "_selected_action": str(participant.pk),
        })
        self.assertContains(response, "closure blocked")
        self.assertContains(response, "retention hold")
        self.assertNotContains(response, "registry milestone has no run records")

    def test_confirm_post_cannot_bypass_a_new_hold(self):
        participant = self.participant(retention_hold=True)
        administrator = Participant.objects.create_superuser(email="admin@example.test", nickname="Admin", password="test-password")
        self.client.force_login(administrator)
        self.client.post(reverse("admin:registry_participant_changelist"), {
            "action": "process_account_closures", "_selected_action": str(participant.pk), "confirm": "yes",
        })
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(AccountClosureRecord.objects.exists())

    def test_cleanup_does_not_delete_a_still_referenced_avatar(self):
        participant = self.participant()
        participant.avatar.save("shared.webp", ContentFile(b"test"))
        RetentionFileDeletion.objects.create(kind="avatar", name=participant.avatar.name)
        self.assertEqual(drain_file_deletions(), (0, 1))
        self.assertTrue(Path(participant.avatar.path).exists())


class AccountRetentionMigrationTests(TransactionTestCase):
    def test_populated_upgrade_preserves_account_and_legacy_ownership(self):
        previous = [("registry", "0075_merge_reading_cooked_food")]
        current = [("registry", "0084_legacy_identity_removal")]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            old_apps = executor.loader.project_state(previous).apps
            account = old_apps.get_model("registry", "Participant").objects.create(
                email="upgrade@example.test", normalized_email="upgrade@example.test",
                nickname="Upgrade", normalized_nickname="upgrade", password="preserve-password-hash",
            )
            run = old_apps.get_model("registry", "LegacyRun").objects.create(
                source_key="upgrade", normalized_legacy_name="historic upgrade",
                legacy_participant_name="Historic Upgrade", claimed_participant_id=account.pk,
            )
            MigrationExecutor(connection).migrate(current)
            migrated = Participant.objects.get(pk=account.pk)
            self.assertEqual(migrated.password, "preserve-password-hash")
            self.assertFalse(migrated.retention_hold)
            self.assertEqual(LegacyRun.objects.get(pk=run.pk).claimed_participant_id, account.pk)
            self.assertFalse(LegacyRun.objects.get(pk=run.pk).identity_removed)
            self.assertFalse(RetentionFileDeletion.objects.exists())
        finally:
            MigrationExecutor(connection).migrate(current)
