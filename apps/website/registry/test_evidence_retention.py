from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import connection, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from .evidence_retention import retire_run_evidence, retire_workshop_notes, two_year_cutoff
from .legacy_imports import build_legacy_import_preview
from .models import LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Participant, WorkshopMod, WorkshopModVote


class EvidenceRetentionTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.old = two_year_cutoff(self.now) - timedelta(days=1)
        self.user = Participant.objects.create_user(email="retention@example.test", nickname="Retention", password="test-only")
        self.run = LegacyRun.objects.create(source_key="retained", normalized_legacy_name="retained", legacy_participant_name="Retained", claimed_participant=self.user, lifecycle="inactive")
        self.submission = LegacyRunSubmission.objects.create(run=self.run, source="participant", submitted_by=self.user, status="approved", reviewed_at=self.old, evidence_url="https://example.test/old", review_note="Old note", zombie_kills=123)
        self.claim = LegacyRunClaim.objects.create(run=self.run, participant=self.user, status="approved", reviewed_at=self.old, evidence="Old claim")
        LegacyRun.objects.filter(pk=self.run.pk).update(updated_at=self.old, created_at=self.old, current_submission=self.submission, best_submission=self.submission)
        LegacyRunSubmission.objects.filter(pk=self.submission.pk).update(submitted_at=self.old)
        LegacyRunClaim.objects.filter(pk=self.claim.pk).update(submitted_at=self.old)

    def test_preview_is_read_only_then_apply_clears_evidence_without_losing_results(self):
        output = StringIO()
        call_command("apply_evidence_retention", stdout=output)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.evidence_url, "https://example.test/old")
        self.assertIn("eligible=1", output.getvalue())
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "eligible")
        self.submission.refresh_from_db()
        self.claim.refresh_from_db()
        self.run.refresh_from_db()
        self.assertEqual(self.submission.evidence_url, "")
        self.assertEqual(self.submission.zombie_kills, 123)
        self.assertEqual(self.claim.evidence, "")
        self.assertEqual(self.claim.status, "approved")
        self.assertEqual(self.run.claimed_participant_id, self.user.pk)
        self.assertEqual(self.run.best_submission_id, self.submission.pk)
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "empty")

    def test_active_run_evidence_does_not_expire(self):
        LegacyRun.objects.filter(pk=self.run.pk).update(lifecycle="active")
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "retained")
        self.submission.refresh_from_db()
        self.assertTrue(self.submission.evidence_url)

    def test_latest_run_or_decision_date_and_pending_work_prevent_expiry(self):
        for model, field, value in (
            (LegacyRun, "updated_at", self.now),
            (LegacyRunSubmission, "reviewed_at", self.now),
            (LegacyRunClaim, "reviewed_at", self.now),
            (LegacyRunClaim, "status", "pending"),
        ):
            obj = self.run if model is LegacyRun else self.submission if model is LegacyRunSubmission else self.claim
            with self.subTest(field=field, model=model.__name__):
                before = model.objects.values_list(field, flat=True).get(pk=obj.pk)
                model.objects.filter(pk=obj.pk).update(**{field: value})
                self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "retained")
                model.objects.filter(pk=obj.pk).update(**{field: before})

    def test_hold_preserves_evidence(self):
        Participant.objects.filter(pk=self.user.pk).update(retention_hold=True)
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "held")
        self.submission.refresh_from_db()
        self.assertTrue(self.submission.evidence_url)

    def test_source_retirement_preserves_other_rows_and_the_public_identity(self):
        source = "Position,Name,Zombies Killed,Survival Time Days,Outposts Cleared,Level 10 Skills,Overall Challenge Progress,Channel\n1,Retained,123,3,1,1,5,private-link\n2,Other,222,4,1,1,5,other-link\n"
        review = LegacyDataImport.objects.create(status="imported", imported_at=self.old, leaderboard_csv=source, hall_of_fame_csv=source, preview=build_legacy_import_preview(source, source))
        LegacyDataImport.objects.filter(pk=review.pk).update(uploaded_at=self.old)
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "eligible")
        review.refresh_from_db()
        self.run.refresh_from_db()
        self.assertNotIn("private-link", review.leaderboard_csv)
        self.assertIn("other-link", review.leaderboard_csv)
        self.assertIsNotNone(review.redacted_at)
        self.assertEqual(self.run.legacy_participant_name, "Retained")
        self.assertFalse(self.run.identity_removed)

    def test_recent_source_review_defers_expiry(self):
        source = "Position,Name,Zombies Killed,Survival Time Days,Outposts Cleared,Level 10 Skills,Overall Challenge Progress\n1,Retained,123,3,1,1,5\n"
        LegacyDataImport.objects.create(status="preview", leaderboard_csv=source, hall_of_fame_csv=source, preview=build_legacy_import_preview(source, source))
        self.assertEqual(retire_run_evidence(self.run.pk, apply=True, now=self.now), "retained")

    def test_workshop_notes_expire_but_public_policy_and_decisions_remain(self):
        mod = WorkshopMod.objects.create(workshop_id="333333", title="Public mod", ruling="allowed", public_rationale="Current published policy", submission_reason="Old evidence", unstable_ruling_notes="Old review", submitted_by=self.user, reviewed_at=self.old)
        vote = WorkshopModVote.objects.create(workshop_mod=mod, voter=self.user, voter_name="Retention", decision="allow", reason="Old vote evidence")
        WorkshopMod.objects.filter(pk=mod.pk).update(created_at=self.old, updated_at=self.old)
        WorkshopModVote.objects.filter(pk=vote.pk).update(created_at=self.old, updated_at=self.old)
        self.assertEqual(retire_workshop_notes(mod.pk, apply=True, now=self.now), "eligible")
        mod.refresh_from_db()
        vote.refresh_from_db()
        self.assertEqual(mod.public_rationale, "Current published policy")
        self.assertEqual(mod.ruling, "allowed")
        self.assertEqual(mod.submission_reason, "")
        self.assertEqual(vote.decision, "allow")
        self.assertEqual(vote.reason, "")

    def test_leap_day_cutoff_uses_calendar_years(self):
        leap = self.now.replace(year=2024, month=2, day=29)
        cutoff = two_year_cutoff(leap)
        self.assertEqual((cutoff.year, cutoff.month, cutoff.day), (2022, 2, 28))

    def test_preview_never_requests_row_locks_but_apply_keeps_them(self):
        mod = WorkshopMod.objects.create(workshop_id="444444", submitted_by=self.user)
        with patch.object(QuerySet, "select_for_update", side_effect=AssertionError("Preview requested a lock")):
            self.assertEqual(retire_run_evidence(self.run.pk, now=self.now), "eligible")
            self.assertEqual(retire_workshop_notes(mod.pk, now=self.now), "retained")
        locked = set()
        original = QuerySet.select_for_update

        def record_lock(queryset, *args, **kwargs):
            locked.add(queryset.model)
            return original(queryset, *args, **kwargs)

        with patch.object(QuerySet, "select_for_update", record_lock):
            retire_run_evidence(self.run.pk, apply=True, now=self.now)
            retire_workshop_notes(mod.pk, apply=True, now=self.now)
        self.assertTrue({Participant, LegacyRun, LegacyRunSubmission, LegacyRunClaim,
                         WorkshopMod, WorkshopModVote}.issubset(locked))


class ReadOnlyEvidencePreviewTests(TransactionTestCase):
    setUp = EvidenceRetentionTests.setUp

    @skipUnlessDBFeature("has_select_for_update")
    def test_command_runs_in_postgresql_read_only_transaction(self):
        WorkshopMod.objects.create(workshop_id="555555", ruling="allowed", submitted_by=self.user)
        output = StringIO()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            call_command("apply_evidence_retention", stdout=output)
        self.assertIn("eligible=1", output.getvalue())
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.evidence_url, "https://example.test/old")
