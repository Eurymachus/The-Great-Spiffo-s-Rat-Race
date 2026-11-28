import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from config.release_controls import CONTROLS, parse_release_control
from operations import leaderboard_publish
from pages.community_stats import build_community_stats
from pages.models import Page, PageBlock, PageSection
from registry.leaderboard import build_ranking_table
from registry.models import (
    ChallengeRun, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Participant,
    RunSubmission, WorkshopMod,
)
from registry.submission_approval import ApprovalBlocked, approve_submission, route_run


class ReleaseConfigurationTests(SimpleTestCase):
    def test_missing_environment_closes_every_control(self):
        environment = {key: value for key, value in os.environ.items() if key not in CONTROLS.values()}
        result = subprocess.run(
            [sys.executable, "-c", "from config import settings; from config.release_controls import CONTROLS; assert all(getattr(settings, name) is False for name in CONTROLS.values())"],
            env=environment, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_switch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RR2_ENABLED"):
            parse_release_control("treu", name="RR2_ENABLED")
        self.assertFalse(parse_release_control("false", name="RR2_ENABLED"))
        self.assertTrue(parse_release_control("true", name="RR2_ENABLED"))


@override_settings(
    REGISTRATION_ENABLED=False, WORKSHOP_SUBMISSIONS_ENABLED=False,
    RR1_SUBMISSIONS_ENABLED=False, RR2_ENABLED=False,
    SITE_MAINTENANCE_MODE=False,
)
class ReleaseBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.racer = Participant.objects.create_user(
            email="release@example.com", nickname="ReleaseRacer", password="test-password",
            status=Participant.Status.VERIFIED, is_active=True,
        )
        cls.staff = Participant.objects.create_superuser(
            email="release-staff@example.com", nickname="ReleaseStaff", password="test-password",
            status=Participant.Status.VERIFIED,
        )
        cls.tracked_run = ChallengeRun.objects.create(
            participant=cls.racer, run_id="release-boundary", character_name="Hidden RR2 Character",
            export_format=4, generated_at=timezone.now(), event_hash="a" * 64,
            status=ChallengeRun.Status.OFFICIAL,
        )
        cls.submission = RunSubmission.objects.create(
            run=cls.tracked_run, submitter=cls.racer, export_format=4, generated_at=timezone.now(),
            event_hash="a" * 64, checksum="b" * 64, raw_export="must never be decoded",
        )
        cls.tracked_run.approved_submission = cls.submission
        cls.tracked_run.save(update_fields=["approved_submission"])
        cls.legacy = LegacyRun.objects.create(
            source_key="release-legacy", normalized_legacy_name="historical racer",
            legacy_participant_name="Historical Racer", claimed_participant=cls.racer,
        )
        result = LegacyRunSubmission.objects.create(
            run=cls.legacy, source=LegacyRunSubmission.Source.IMPORT_LEADERBOARD,
            status=LegacyRunSubmission.Status.APPROVED, zombie_kills=1234,
        )
        cls.legacy.current_submission = result
        cls.legacy.best_submission = result
        cls.legacy.save(update_fields=["current_submission", "best_submission"])
        cls.mod = WorkshopMod.objects.create(
            workshop_id="1234567890", title="Published Mod", ruling=WorkshopMod.Ruling.ALLOWED,
        )

    def test_rr2_direct_routes_block_every_role_before_decoding(self):
        routes = [
            reverse("registry:submit_run"),
            reverse("registry:update_run_submission_evidence", args=[self.submission.pk]),
            reverse("registry:deactivate_run", args=[self.tracked_run.pk]),
            reverse("registry:public_run_detail", args=[self.tracked_run.pk]),
            reverse("registry:leaderboard"),
        ]
        before = list(RunSubmission.objects.values())
        with patch("registry.views.decode_run_export_cached") as decode:
            for user in [None, self.racer, self.staff]:
                self.client.logout()
                if user:
                    self.client.force_login(user)
                for path in routes:
                    for method in ["get", "post"]:
                        with self.subTest(user=user, path=path, method=method):
                            response = getattr(self.client, method)(path)
                            self.assertEqual(response.status_code, 403)
                            self.assertIn("no-store", response["Cache-Control"])
            decode.assert_not_called()
        self.assertEqual(list(RunSubmission.objects.values()), before)
        self.tracked_run.refresh_from_db()
        self.assertIsNone(self.tracked_run.participant_deactivated_at)

    def test_closed_intake_blocks_writes_but_keeps_accounts_and_results(self):
        self.client.force_login(self.racer)
        with patch("registry.views.fetch_project_zomboid_workshop_item") as steam:
            for path in ["/signup/", "/signup/validate/", "/mods/", "/account/legacy/submit/",
                         reverse("registry:claim_legacy_run", args=[self.legacy.pk])]:
                self.assertEqual(self.client.post(path, {"workshop_id": "9999999999"}).status_code, 403)
            self.assertEqual(self.client.get("/mods/workshop-lookup/?q=1234567890").status_code, 403)
            steam.assert_not_called()
        self.assertEqual(LegacyRunClaim.objects.count(), 0)
        self.assertEqual(LegacyRunSubmission.objects.count(), 1)
        for path in ["/account/", "/account/settings/", "/account/data/", "/mods/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.client.logout()
        for path in ["/login/", "/resend/", "/password-reset/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_shared_pages_hide_rr2_but_preserve_legacy(self):
        self.client.force_login(self.racer)
        for path in ["/account/", "/account/dashboard/fragment/",
                     reverse("registry:participant_profile", args=[self.racer.pk])]:
            response = self.client.get(path)
            self.assertContains(response, "Historical Racer")
            self.assertNotContains(response, "Hidden RR2 Character")
            self.assertNotContains(response, 'href="/account/submit/"')
            self.assertNotContains(response, 'href="/account/legacy/submit/"')
            self.assertNotContains(response, "Personal Best")
        self.assertEqual(ChallengeRun.objects.count(), 1)

    def test_managed_rankings_and_statistics_cannot_bypass_gate(self):
        page = Page.objects.create(title="Mixed results", slug="mixed-results", public_path="mixed-results")
        section = PageSection.objects.create(page=page, name="Results")
        PageBlock.objects.create(section=section, block_type="ranking_table")
        PageBlock.objects.create(section=section, block_type="community_stats")
        PageBlock.objects.create(section=section, block_type="ranking_table", ranking_config={"source": "legacy_leaderboard"})
        response = self.client.get("/mixed-results/")
        self.assertContains(response, "ReleaseRacer")
        self.assertNotContains(response, "Hidden RR2 Character")
        self.assertNotContains(response, 'class="community-stats"')
        self.assertEqual(response.content.count(b'class="managed-ranking-table"'), 1)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(build_ranking_table(), [])
            self.assertEqual(build_community_stats()["metrics"], [])
            self.assertEqual(build_community_stats({"metrics": ["unfinished-metric"]})["metrics"], [])
        self.assertTrue(all("administration_releaseconfiguration" in query["sql"] for query in queries))

    def test_admin_has_no_rr2_bypass_and_keeps_workshop_review(self):
        self.client.force_login(self.staff)
        paths = [reverse("admin:registry_runsubmission_approve", args=[self.submission.pk]),
                 reverse("admin:registry_challengerun_change", args=[self.tracked_run.pk]),
                 reverse("admin:registry_runsubmission_audit", args=[self.submission.pk]),
                 reverse("admin:operations_dailyleaderboardschedule_run_now", args=[1]),
                 reverse("admin:operations_rundatadangerzone_changelist")]
        for path in paths:
            for method in ["get", "post"]:
                self.assertEqual(getattr(self.client, method)(path).status_code, 403, path)
        response = self.client.get("/admin/")
        self.assertContains(response, "Mod submission reviews")
        self.assertNotContains(response, "2.0 submissions")
        self.assertNotContains(response, reverse("admin:registry_challengerun_changelist"))
        self.assertEqual(self.client.get(reverse("admin:registry_workshopmod_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:registry_legacyrun_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:autocomplete"), {
            "app_label": "registry", "model_name": "challengerun", "field_name": "challenge_mode",
        }).status_code, 403)

    def test_worker_and_approval_do_not_touch_dormant_records(self):
        before = list(RunSubmission.objects.values())
        with patch("registry.submission_approval.decode_run_export_cached") as decode:
            with self.assertRaises(ApprovalBlocked):
                approve_submission(self.submission.pk, self.staff)
            with self.assertRaises(ApprovalBlocked):
                approve_submission(self.submission.pk, automatic=True)
            route_run(self.tracked_run.pk)
            leaderboard_publish.tick()
            with self.assertRaises(ValueError):
                leaderboard_publish.enqueue()
            decode.assert_not_called()
        self.assertEqual(list(RunSubmission.objects.values()), before)

    @override_settings(REGISTRATION_ENABLED=True)
    def test_registration_opens_independently(self):
        self.assertEqual(self.client.get("/signup/").status_code, 200)
        self.assertEqual(self.client.get("/account/submit/").status_code, 403)
        self.assertEqual(self.client.post("/mods/").status_code, 403)

    @override_settings(WORKSHOP_SUBMISSIONS_ENABLED=True)
    def test_workshop_opens_independently(self):
        self.client.force_login(self.racer)
        with patch("registry.views.fetch_project_zomboid_workshop_item", return_value={
            "workshop_id": "9999999999", "title": "New Mod",
            "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=9999999999",
        }):
            self.assertEqual(self.client.post("/mods/", {"workshop_id": "9999999999", "reason": "Review this mod"}).status_code, 302)
        self.assertEqual(WorkshopMod.objects.get(workshop_id="9999999999").ruling, "pending")
        self.assertEqual(self.client.get("/signup/").status_code, 403)

    @override_settings(RR1_SUBMISSIONS_ENABLED=True)
    def test_rr1_opens_independently(self):
        self.client.force_login(self.staff)
        unclaimed = LegacyRun.objects.create(source_key="claimable", normalized_legacy_name="claimable", legacy_participant_name="Claimable")
        response = self.client.post(reverse("registry:claim_legacy_run", args=[unclaimed.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LegacyRunClaim.objects.filter(run=unclaimed, participant=self.staff).exists())
        self.client.force_login(self.racer)
        self.assertEqual(self.client.get("/account/legacy/submit/").status_code, 200)
        self.assertContains(self.client.get("/account/"), 'href="/account/legacy/submit/"')
        self.assertEqual(self.client.get("/account/submit/").status_code, 403)

    @override_settings(RR2_ENABLED=True)
    def test_rr2_can_be_explicitly_enabled_for_development(self):
        self.client.force_login(self.racer)
        self.assertEqual(self.client.get("/account/submit/").status_code, 200)
        with patch("registry.views.decode_run_export_cached") as decode:
            self.client.post("/account/submit/", {})
            decode.assert_not_called()  # Normal form validation still applies.
        self.assertEqual(self.client.get("/signup/").status_code, 403)

    def test_health_reports_effective_controls(self):
        self.assertEqual(self.client.get("/health/live/").json()["features"], {
            "registration": False, "workshop_submissions": False,
            "rr1_submissions": False, "rr2": False,
        })

    def test_closed_links_and_forms_are_not_advertised(self):
        for path in ["/", "/mods/", "/login/"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'href="/signup/')
            self.assertNotContains(response, 'href="/leaderboard/')
            self.assertNotContains(response, 'data-mod-submit-open')
            self.assertNotContains(response, 'data-mod-review-form')

    def test_switching_intake_off_does_not_disable_existing_account_verification(self):
        from registry.tokens import create_verification_token
        pending = Participant.objects.create_user(
            email="pending-release@example.com", nickname="PendingRelease",
            password="test-password", status=Participant.Status.PENDING, is_active=False,
        )
        response = self.client.get(reverse("registry:verify", args=[create_verification_token(pending)]))
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, Participant.Status.VERIFIED)
