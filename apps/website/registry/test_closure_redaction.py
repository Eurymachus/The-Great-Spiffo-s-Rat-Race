import csv
import io
import time
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from pages.ranking_config import default_ranking_config
from pages.templatetags.ranking_table import managed_ranking_table
from .closure_redaction import build_redaction_plan, review_details, review_token
from .legacy_imports import apply_legacy_import, build_legacy_import_preview
from .models import (
    AccountClosureRecord, ChallengeRun, LegacyDataImport, LegacyRun, LegacyRunClaim,
    LegacyRunSubmission, Participant, WorkshopMod, WorkshopModVote,
)
from .retention import AccountDeletionBlocked, close_account


class ClosureRedactionTests(TestCase):
    def setUp(self):
        self.leaving = Participant.objects.create_user(
            email="leaving@example.test", nickname="Leaving", password="test-only",
            status="verified", deletion_requested_at=timezone.now(),
        )
        self.other = Participant.objects.create_user(email="other@example.test", nickname="Other", password="test-only", status="verified")
        self.admin = Participant.objects.create_superuser(email="admin@example.test", nickname="Admin", password="test-only")
        self.run = LegacyRun.objects.create(
            source_key="old-name-hash", normalized_legacy_name="historic leaving",
            legacy_participant_name="Historic Leaving", character_name="Private Character",
            claimed_participant=self.leaving,
        )
        self.submission = LegacyRunSubmission.objects.create(
            run=self.run, submitted_by=self.leaving, status="approved", source="participant",
            zombie_kills=12345, survival_days="12.5", outposts_cleared=2, maxed_skills=3,
            challenge_progress="14.5", character_name="Private Character", review_note="private note",
            evidence_url="https://example.test/private", evidence_title="Historic Leaving",
        )
        self.run.current_submission = self.submission
        self.run.best_submission = self.submission
        self.run.save()
        self.claim = LegacyRunClaim.objects.create(run=self.run, participant=self.leaving, status="approved", evidence="private claim")
        output = io.StringIO()
        csv.writer(output).writerows([
            ["Position", "Name", "Zombies Killed", "Survival Time Days", "Outposts Cleared", "Level 10 Skills", "Overall Challenge Progress", "Channel"],
            [1, "Historic Leaving", 12345, "12.5", 2, 3, "14.5", "https://example.test/private"],
            [2, "Other Historic", 500, 4, 1, 1, 5, "https://example.test/other"],
        ])
        source = output.getvalue()
        self.source = LegacyDataImport.objects.create(
            status="imported", leaderboard_csv=source, hall_of_fame_csv=source,
            leaderboard_filename="original.csv", hall_of_fame_filename="original-hall.csv",
            leaderboard_sha256="original-hash", hall_of_fame_sha256="original-hash",
            preview=build_legacy_import_preview(source, source),
        )
        self.submission.import_review = self.source
        self.submission.save()

    def token(self):
        return review_token(self.leaving, build_redaction_plan(self.leaving))

    def test_reviewed_closure_preserves_scores_and_removes_identity_from_sources(self):
        other_run = LegacyRun.objects.create(source_key="other", normalized_legacy_name="other historic", legacy_participant_name="Other Historic", claimed_participant=self.other)
        before_other = list(LegacyRun.objects.filter(pk=other_run.pk).values())
        close_account(self.leaving.pk, redaction_token=self.token())
        self.run.refresh_from_db()
        self.submission.refresh_from_db()
        self.source.refresh_from_db()
        self.assertFalse(Participant.objects.filter(pk=self.leaving.pk).exists())
        self.assertTrue(self.run.identity_removed)
        self.assertIsNone(self.run.claimed_participant_id)
        self.assertEqual(self.run.legacy_participant_name, "Former Rat Racer")
        self.assertNotEqual(self.run.source_key, "old-name-hash")
        self.assertNotIn("historic", self.run.normalized_legacy_name)
        self.assertEqual(self.run.current_submission_id, self.submission.pk)
        self.assertEqual(self.run.best_submission_id, self.submission.pk)
        self.assertEqual(self.submission.zombie_kills, 12345)
        self.assertEqual(str(self.submission.survival_days), "12.50000")
        self.assertEqual(self.submission.character_name, "")
        self.assertEqual(self.submission.evidence_url, "")
        self.assertEqual(self.submission.review_note, "")
        self.assertFalse(LegacyRunClaim.objects.filter(pk=self.claim.pk).exists())
        self.assertNotIn("Historic Leaving", self.source.leaderboard_csv)
        self.assertNotIn("example.test/private", self.source.hall_of_fame_csv)
        self.assertIn("Other Historic", self.source.leaderboard_csv)
        self.assertIn("example.test/other", self.source.hall_of_fame_csv)
        self.assertEqual(len(self.source.preview["records"]), 1)
        self.assertIsNotNone(self.source.redacted_at)
        self.assertNotEqual(self.source.leaderboard_sha256, "original-hash")
        self.assertEqual(list(LegacyRun.objects.filter(pk=other_run.pk).values()), before_other)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:registry_legacydataimport_change", args=(self.source.pk,)))
        self.assertContains(response, "Retained source preview")
        self.assertNotContains(response, "Confirm and replace Rat Race 1.0 data")

    def test_stale_review_blocks_without_partial_redaction(self):
        token = self.token()
        LegacyRunSubmission.objects.filter(pk=self.submission.pk).update(evidence_title="new evidence")
        with self.assertRaisesMessage(AccountDeletionBlocked, "Related records changed"):
            close_account(self.leaving.pk, redaction_token=token)
        self.run.refresh_from_db()
        self.assertFalse(self.run.identity_removed)
        self.assertFalse(AccountClosureRecord.objects.exists())

    def test_expired_or_forged_review_cannot_delete(self):
        token = self.token()
        with patch("django.core.signing.time.time", return_value=time.time() + 3700):
            with self.assertRaises(AccountDeletionBlocked):
                close_account(self.leaving.pk, redaction_token=token)
        with self.assertRaises(AccountDeletionBlocked):
            close_account(self.leaving.pk, redaction_token="forged")

    def test_rollback_restores_history_and_sources(self):
        original = self.source.leaderboard_csv
        with patch.object(Participant, "delete", side_effect=RuntimeError("Database failure")):
            with self.assertRaises(RuntimeError):
                close_account(self.leaving.pk, redaction_token=self.token())
        self.run.refresh_from_db()
        self.source.refresh_from_db()
        self.assertFalse(self.run.identity_removed)
        self.assertEqual(self.run.claimed_participant_id, self.leaving.pk)
        self.assertEqual(self.source.leaderboard_csv, original)
        self.assertTrue(LegacyRunClaim.objects.filter(pk=self.claim.pk).exists())
        self.assertFalse(AccountClosureRecord.objects.exists())

    def test_other_claimants_hold_prevents_shared_evidence_redaction(self):
        self.other.retention_hold = True
        self.other.save()
        LegacyRunClaim.objects.create(run=self.run, participant=self.other, evidence="disputed")
        with self.assertRaisesMessage(AccountDeletionBlocked, "retention hold"):
            close_account(self.leaving.pk, redaction_token=self.token())

    def test_closed_run_cannot_be_claimed_reassigned_or_reimported(self):
        close_account(self.leaving.pk, redaction_token=self.token())
        self.client.force_login(self.other)
        response = self.client.post(reverse("registry:claim_legacy_run", args=(self.run.pk,)))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LegacyRunClaim.objects.filter(run=self.run).exists())
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LegacyRun.objects.filter(pk=self.run.pk).update(claimed_participant=self.other)
        self.source.refresh_from_db()
        with self.assertRaises(ValidationError):
            apply_legacy_import(self.source, self.admin)

    def test_rankings_show_former_racer_without_claim_action(self):
        close_account(self.leaving.pk, redaction_token=self.token())
        config = default_ranking_config()
        config["source"] = "legacy_leaderboard"
        request = RequestFactory().get("/")
        request.user = self.other
        context = managed_ranking_table({"request": request}, SimpleNamespace(pk=1, ranking_config=config))
        entry = next(item for item in context["entries"] if item["legacy_run"].pk == self.run.pk)
        self.assertEqual(entry["racer"], "Former Rat Racer")
        self.assertIsNone(entry["participant"])
        self.assertEqual(entry["claim_state"], "unavailable")

    def test_workshop_ruling_and_vote_survive_without_personal_text(self):
        mod = WorkshopMod.objects.create(workshop_id="345", title="Public mod", ruling="allowed", submitted_by=self.leaving, submission_reason="my reason", public_rationale="private mention", unstable_ruling_notes="private note")
        vote = WorkshopModVote.objects.create(workshop_mod=mod, voter=self.leaving, voter_name="Leaving", decision="allow", reason="private reason")
        close_account(self.leaving.pk, redaction_token=self.token())
        mod.refresh_from_db()
        vote.refresh_from_db()
        self.assertEqual((mod.title, mod.ruling), ("Public mod", "allowed"))
        self.assertEqual((mod.submission_reason, mod.public_rationale, mod.unstable_ruling_notes), ("", "", ""))
        self.assertIsNone(mod.submitted_by_id)
        self.assertEqual((vote.voter_name, vote.decision, vote.reason), ("Former Rat Racer", "allow", ""))

    def test_admin_log_identity_is_removed_but_other_logs_remain(self):
        removed = LogEntry.objects.create(user=self.admin, content_type=ContentType.objects.get_for_model(LegacyRunSubmission), object_id=str(self.submission.pk), object_repr="Historic Leaving", action_flag=CHANGE)
        account_log = LogEntry.objects.create(user=self.admin, content_type=ContentType.objects.get_for_model(Participant), object_id=str(self.leaving.pk), object_repr="Leaving", change_message="leaving@example.test", action_flag=CHANGE)
        kept = LogEntry.objects.create(user=self.admin, content_type=ContentType.objects.get_for_model(Participant), object_id=str(self.other.pk), object_repr="Other", action_flag=CHANGE)
        close_account(self.leaving.pk, redaction_token=self.token())
        removed.refresh_from_db()
        self.assertEqual(removed.object_repr, "Redacted record")
        self.assertEqual(removed.user_id, self.admin.pk)
        self.assertEqual(removed.action_flag, CHANGE)
        account_log.refresh_from_db()
        self.assertIsNone(account_log.object_id)
        self.assertEqual(account_log.object_repr, "Redacted record")
        self.assertNotIn("example.test", account_log.change_message)
        self.assertTrue(LogEntry.objects.filter(pk=kept.pk).exists())

    def test_preview_shows_only_affected_rows_of_shared_sources(self):
        details = review_details(build_redaction_plan(self.leaving))
        self.assertIn("Historic Leaving", details)
        self.assertIn("example.test/private", details)
        self.assertNotIn("Other Historic", details)
        self.assertNotIn("example.test/other", details)

    def test_admin_confirmation_requires_reviewed_preview(self):
        self.client.force_login(self.admin)
        url = reverse("admin:registry_participant_changelist")
        selection = {"action": "process_account_closures", "_selected_action": str(self.leaving.pk)}
        preview = self.client.post(url, selection)
        self.assertContains(preview, "Inspect affected records")
        token = preview.context["history_reviews"][0]["token"]
        self.client.post(url, {**selection, "confirm": "yes", f"redaction_token_{self.leaving.pk}": token})
        self.assertTrue(Participant.objects.filter(pk=self.leaving.pk).exists())
        response = self.client.post(url, {**selection, "confirm": "yes", "reviewed_redaction": "yes", f"redaction_token_{self.leaving.pk}": token})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Participant.objects.filter(pk=self.leaving.pk).exists())

    def test_rr2_history_remains_blocked(self):
        ChallengeRun.objects.create(participant=self.leaving, run_id="contract-deferred", export_format=1, generated_at=timezone.now())
        with self.assertRaises(AccountDeletionBlocked):
            close_account(self.leaving.pk, redaction_token=self.token())

    def test_malformed_shared_source_blocks_redaction(self):
        LegacyDataImport.objects.filter(pk=self.source.pk).update(leaderboard_csv="unrecognised source")
        with self.assertRaisesMessage(AccountDeletionBlocked, "unrecognised columns"):
            build_redaction_plan(self.leaving)

    def test_other_pending_claim_is_declined_and_cannot_be_approved(self):
        other_claim = LegacyRunClaim.objects.create(run=self.run, participant=self.other, evidence="Historic Leaving")
        close_account(self.leaving.pk, redaction_token=self.token())
        other_claim.refresh_from_db()
        self.assertEqual(other_claim.status, "declined")
        self.assertEqual(other_claim.evidence, "")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:registry_legacyrunclaim_approve", args=(other_claim.pk,)))
        self.assertEqual(response.status_code, 302)
        self.run.refresh_from_db()
        self.assertIsNone(self.run.claimed_participant_id)

    def test_reviewer_closure_preserves_another_submitters_evidence(self):
        other_run = LegacyRun.objects.create(source_key="other", normalized_legacy_name="other", legacy_participant_name="Other", claimed_participant=self.other)
        other_submission = LegacyRunSubmission.objects.create(
            run=other_run, submitted_by=self.other, reviewed_by=self.leaving,
            source="participant", status="approved", character_name="Other character",
            evidence_url="https://example.test/other-evidence", review_note="Leaving reviewer note",
        )
        other_claim = LegacyRunClaim.objects.create(run=other_run, participant=self.other, reviewed_by=self.leaving, evidence="Other claim evidence", review_note="Leaving reviewer note")
        mod = WorkshopMod.objects.create(workshop_id="567", title="Other mod", submitted_by=self.other, reviewed_by=self.leaving, submission_reason="Other request", public_rationale="Leaving reviewer note")
        close_account(self.leaving.pk, redaction_token=self.token())
        other_submission.refresh_from_db()
        other_claim.refresh_from_db()
        mod.refresh_from_db()
        self.assertEqual(other_submission.evidence_url, "https://example.test/other-evidence")
        self.assertEqual(other_submission.character_name, "Other character")
        self.assertEqual(other_submission.submitted_by_id, self.other.pk)
        self.assertEqual(other_submission.review_note, "")
        self.assertEqual(other_claim.evidence, "Other claim evidence")
        self.assertEqual(other_claim.participant_id, self.other.pk)
        self.assertEqual(mod.submission_reason, "Other request")
        self.assertEqual(mod.submitted_by_id, self.other.pk)

    def test_pending_submission_on_closed_run_cannot_be_approved(self):
        pending = LegacyRunSubmission.objects.create(run=self.run, submitted_by=self.leaving, source="participant", zombie_kills=99999)
        close_account(self.leaving.pk, redaction_token=self.token())
        pending.refresh_from_db()
        self.assertEqual(pending.status, "declined")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:registry_legacyrunsubmission_approve", args=(pending.pk,)))
        self.assertEqual(response.status_code, 404)
        self.run.refresh_from_db()
        self.assertEqual(self.run.current_submission_id, self.submission.pk)

    def test_general_admin_cannot_edit_or_delete_closed_result(self):
        close_account(self.leaving.pk, redaction_token=self.token())
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:registry_legacyrun_change", args=(self.run.pk,)), {"legacy_participant_name": "Reidentified"})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse("admin:registry_legacyrun_delete", args=(self.run.pk,)), {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(LegacyRun.objects.filter(pk=self.run.pk).exists())

    def test_second_closure_requires_new_review_after_shared_source_changes(self):
        self.other.deletion_requested_at = timezone.now()
        self.other.save()
        LegacyRun.objects.create(source_key="other", normalized_legacy_name="other historic", legacy_participant_name="Other Historic", claimed_participant=self.other)
        token = review_token(self.other, build_redaction_plan(self.other))
        close_account(self.leaving.pk, redaction_token=self.token())
        with self.assertRaisesMessage(AccountDeletionBlocked, "Related records changed"):
            close_account(self.other.pk, redaction_token=token)
        close_account(self.other.pk, redaction_token=review_token(self.other, build_redaction_plan(self.other)))
        self.source.refresh_from_db()
        self.assertEqual(self.source.preview["records"], [])
        self.assertNotIn("Other Historic", self.source.leaderboard_csv)
        self.assertEqual(LegacyRun.objects.filter(identity_removed=True).count(), 2)
