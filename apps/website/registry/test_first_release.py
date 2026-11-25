from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Participant,
    StreamingAccount, WorkshopMod, WorkshopModVote,
)
from .steam_workshop import SteamWorkshopError


@override_settings(RR2_ENABLED=False, RR1_SUBMISSIONS_ENABLED=False, WORKSHOP_SUBMISSIONS_ENABLED=False)
class FirstReleaseDownloadTests(TestCase):
    def setUp(self):
        self.owner = Participant.objects.create_user(email="owner@example.test", nickname="Owner", password="test-only", status="verified", admin_notes="staff-only-secret")
        self.other = Participant.objects.create_user(email="other@example.test", nickname="Other", password="test-only", status="verified")
        self.run = LegacyRun.objects.create(source_key="owner", normalized_legacy_name="owner", legacy_participant_name="Historic Owner", claimed_participant=self.owner)
        self.claim = LegacyRunClaim.objects.create(run=self.run, participant=self.owner, status="declined", evidence="owner-claim-evidence", review_note="owner-facing-decision")
        self.update = LegacyRunSubmission.objects.create(run=self.run, submitted_by=self.owner, source="participant", status="declined", evidence_url="https://example.test/owner", review_note="owner-update-decision", zombie_kills=420)
        LegacyRunSubmission.objects.create(run=self.run, submitted_by=self.owner, source="participant", status="approved", review_note="private-approval-note")
        imported = LegacyRunSubmission.objects.create(run=self.run, submitted_by=self.other, source="import_leaderboard", status="approved", zombie_kills=400, evidence_title="other-private-evidence", review_note="other-private-note")
        self.run.best_submission = imported
        self.run.current_submission = imported
        self.run.save()
        self.mod = WorkshopMod.objects.create(workshop_id="111111", title="Owner mod", submitted_by=self.owner, submission_reason="owner-reason", unstable_ruling_notes="staff-mod-note")
        WorkshopMod.objects.create(workshop_id="222222", title="Other mod", submitted_by=self.other, submission_reason="other-mod-reason")
        WorkshopModVote.objects.create(workshop_mod=self.mod, voter=self.owner, voter_name="Owner", decision="allow", reason="owner-vote")
        WorkshopModVote.objects.create(workshop_mod=self.mod, voter=self.other, voter_name="Other", decision="disallow", reason="other-private-vote")
        StreamingAccount.objects.create(participant=self.owner, provider="twitch", provider_identity="owner", encrypted_access_token="access-secret", encrypted_refresh_token="refresh-secret")

    def test_download_covers_owned_records_even_with_intake_and_rr2_closed(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("registry:download_my_data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload["participant"]
        self.assertEqual(payload["format_version"], 2)
        self.assertEqual(data["workshop_requests"][0]["submission_reason"], "owner-reason")
        self.assertEqual(data["workshop_votes"][0]["reason"], "owner-vote")
        self.assertEqual(data["rr1_claims"][0]["evidence"], "owner-claim-evidence")
        self.assertEqual(data["rr1_submissions"][0]["review_note"], "owner-update-decision")
        self.assertEqual(data["rr1_runs"][0]["best_result"]["zombie_kills"], 400)
        for secret in ("staff-only-secret", "staff-mod-note", "private-approval-note", "other-private-evidence", "other-private-note", "other-mod-reason", "other-private-vote", "access-secret", "refresh-secret"):
            self.assertNotContains(response, secret)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_cannot_select_another_account_and_requires_login(self):
        url = reverse("registry:download_my_data")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        response = self.client.get(url, {"participant": str(self.owner.pk)})
        self.assertEqual(response.json()["participant"]["id"], str(self.other.pk))
        self.assertNotContains(response, "owner-claim-evidence")
        self.assertNotContains(response, "owner-reason")


@override_settings(RR2_ENABLED=False, RR1_SUBMISSIONS_ENABLED=True)
class FirstReleaseReviewerTests(TestCase):
    def setUp(self):
        call_command("bootstrap_roles", stdout=StringIO())
        self.owner = Participant.objects.create_user(email="owner@example.test", nickname="Owner", password="test-only", status="verified")
        self.run = LegacyRun.objects.create(source_key="owner", normalized_legacy_name="owner", legacy_participant_name="Historic Owner")
        self.claim = LegacyRunClaim.objects.create(run=self.run, participant=self.owner)

    def reviewer(self, role):
        user = Participant.objects.create_user(email="reviewer@example.test", nickname="Reviewer", password="test-only", status="verified")
        user.groups.add(Group.objects.get(name=role))
        user.refresh_from_db()
        self.client.force_login(user)
        return user

    def test_run_approver_keeps_rr1_permissions_after_repeated_bootstrap(self):
        user = self.reviewer("Run Submission Approver")
        call_command("bootstrap_roles", stdout=StringIO())
        user = Participant.objects.get(pk=user.pk)
        self.assertTrue(user.has_perm("registry.change_legacyrunclaim"))
        self.assertFalse(user.has_perm("registry.change_legacyrun"))
        self.assertFalse(user.has_perm("registry.delete_legacyrunsubmission"))
        queue = self.client.get(reverse("admin:registry_legacyrun_changelist"), {"workspace": "claims"})
        self.assertEqual(queue.status_code, 200)
        self.assertContains(self.client.get("/admin/"), "1.0 claims")
        self.assertNotContains(self.client.get("/admin/"), "2.0 submissions")
        result = self.client.post(reverse("admin:registry_legacyrunclaim_approve", args=(self.claim.pk,)))
        self.assertEqual(result.status_code, 302)
        self.run.refresh_from_db()
        self.assertEqual(self.run.claimed_participant_id, self.owner.pk)
        submission = LegacyRunSubmission.objects.create(run=self.run, submitted_by=self.owner, source="participant", zombie_kills=123)
        result = self.client.post(reverse("admin:registry_legacyrunsubmission_approve", args=(submission.pk,)))
        self.assertEqual(result.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        self.assertEqual(submission.reviewed_by_id, user.pk)

    def test_challenge_administrator_can_decline_with_a_reason(self):
        self.reviewer("Challenge Administrator")
        result = self.client.post(reverse("admin:registry_legacyrunclaim_decline", args=(self.claim.pk,)), {"reason": "Please provide evidence"})
        self.assertEqual(result.status_code, 302)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, "declined")

    def test_workshop_role_cannot_approve_rr1_claims(self):
        self.reviewer("Workshop Mod Approver")
        result = self.client.post(reverse("admin:registry_legacyrunclaim_approve", args=(self.claim.pk,)))
        self.assertEqual(result.status_code, 404)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, "pending")

    def test_reviewer_cannot_edit_ownership_or_confirm_an_import(self):
        self.reviewer("Run Submission Approver")
        response = self.client.post(reverse("admin:registry_legacyrun_change", args=(self.run.pk,)), {"claimed_participant": str(self.owner.pk)})
        self.assertEqual(response.status_code, 403)
        review = LegacyDataImport.objects.create()
        with patch("registry.admin.apply_legacy_import") as apply_import:
            response = self.client.post(reverse("admin:registry_legacydataimport_confirm", args=(review.pk,)))
        self.assertEqual(response.status_code, 404)
        apply_import.assert_not_called()


@override_settings(WORKSHOP_SUBMISSIONS_ENABLED=True)
class WorkshopSubmissionLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = Participant.objects.create_user(email="rate@example.test", nickname="Rate", password="test-only", status="verified")
        self.client.force_login(self.user)

    def test_failed_upstream_requests_are_limited_before_next_provider_call(self):
        with patch("registry.views.fetch_project_zomboid_workshop_item", side_effect=SteamWorkshopError("Provider unavailable")) as fetch:
            for index in range(5):
                response = self.client.post(reverse("registry:mods"), {"workshop_id": "1234567890", "reason": "Please review this mod"})
                self.assertEqual(response.status_code, 200)
            response = self.client.post(reverse("registry:mods"), {"workshop_id": "1234567890", "reason": "Please review this mod"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(fetch.call_count, 5)
        self.assertFalse(WorkshopMod.objects.filter(workshop_id="1234567890").exists())

    def test_ip_limit_is_independent_of_account_limit(self):
        with patch("registry.views.exceeded", side_effect=[False, True]), patch("registry.views.fetch_project_zomboid_workshop_item") as fetch:
            response = self.client.post(reverse("registry:mods"), {"workshop_id": "1234567890", "reason": "Please review this mod"})
        self.assertEqual(response.status_code, 429)
        fetch.assert_not_called()

    def test_anonymous_request_does_not_call_provider(self):
        self.client.logout()
        with patch("registry.views.fetch_project_zomboid_workshop_item") as fetch:
            response = self.client.post(reverse("registry:mods"), {"workshop_id": "1234567890"})
        self.assertEqual(response.status_code, 302)
        fetch.assert_not_called()
