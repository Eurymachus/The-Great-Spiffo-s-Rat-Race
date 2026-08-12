import re
import tempfile
import uuid
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from asgiref.sync import async_to_sync
from PIL import Image

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from branding.models import SiteBranding
from pages.models import NavigationItem, Page, PageBlock, PageSection
from .admin import export_registrations, promote_to_role
from .avatar_moderation import approve_pending_avatar, reject_pending_avatar
from .models import AccountClosureRecord, LegacyDataImport, LegacyRun, LegacyRunClaim, LegacyRunSubmission, Notification, Participant, StreamingAccount, StreamingMedia
from .tokens import create_verification_token
from .streaming import (
    TWITCH_STATE_SESSION_KEY,
    TwitchIntegrationError,
    decrypt_token,
    encrypt_token,
)
from .discord_integration import DISCORD_STATE_SESSION_KEY
from .youtube_integration import YOUTUBE_STATE_SESSION_KEY
from .leaderboard import build_ranking_table
from .legacy_imports import apply_legacy_import, create_legacy_import_review
from .legacy_submissions import parse_survival_time


class LegacyDataImportTests(TestCase):
    HEADER = (
        "Position,Name,Zombies Killed,Survival Time (Full),Survival Time (Days),"
        "Kills / Day Average,Playtime Approximation,Outposts Cleared,Level 10 Skills,"
        "Overall Challenge Progress,Source\n"
    )

    def upload(self, name, rows):
        content = "Legacy results\nGenerated export\n\n" + self.HEADER + "\n".join(rows) + "\n"
        return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")

    def create_review(self):
        reviewer = Participant.objects.create_superuser(
            email="admin@example.com", nickname="LegacyAdmin", password="valid-test-password"
        )
        return create_legacy_import_review(
            leaderboard_upload=self.upload("leaderboard.csv", [
                "1,Active Racer,100,,12,0,0,2,3,10.5,https://twitch.tv/must-not-be-stored",
                "2,Second Racer,50,,8,0,0,0,1,4.2,https://youtube.com/must-not-be-stored",
            ]),
            hall_of_fame_upload=self.upload("hall.csv", [
                "1,Active Racer,250,,20,0,0,5,8,24.5,https://twitch.tv/ignored",
                "2,Past Racer,200,,16,0,0,4,7,19.5,https://youtube.com/ignored",
            ]),
            uploaded_by=reviewer,
        ), reviewer

    def test_preview_merges_both_files_without_storing_channel_data(self):
        review, reviewer = self.create_review()
        self.assertEqual(review.preview["counts"]["merged_runs"], 3)
        self.assertEqual(review.preview["counts"]["active_runs"], 2)
        self.assertNotIn("twitch.tv", str(review.preview))

        apply_legacy_import(review, reviewer)

        self.assertEqual(LegacyRun.objects.count(), 3)
        active = LegacyRun.objects.get(normalized_legacy_name="active racer")
        past = LegacyRun.objects.get(normalized_legacy_name="past racer")
        self.assertEqual(active.lifecycle, LegacyRun.Lifecycle.ACTIVE)
        self.assertEqual(past.lifecycle, LegacyRun.Lifecycle.INACTIVE)
        self.assertEqual(active.current_submission.zombie_kills, 100)
        self.assertEqual(active.best_submission.zombie_kills, 250)
        self.assertFalse(hasattr(active, "source_url"))

    def test_preview_ignores_sheet_position_and_ranks_by_progress(self):
        reviewer = Participant.objects.create_superuser(
            email="sheet-error@example.com", nickname="SheetErrorAdmin",
            password="valid-test-password",
        )
        review = create_legacy_import_review(
            leaderboard_upload=self.upload("leaderboard.csv", [
                "99,First Racer,100,,12,0,0,2,3,10.5,",
                "#N/A,Formula Error Racer,50,,8,0,0,0,1,4.2,",
            ]),
            hall_of_fame_upload=self.upload("hall.csv", [
                "99,First Racer,250,,20,0,0,5,8,24.5,",
                "1,Formula Error Racer,75,,9,0,0,1,2,6.5,",
            ]),
            uploaded_by=reviewer,
        )

        formula_record = next(
            record for record in review.preview["records"]
            if record["normalised_name"] == "formula error racer"
        )
        self.assertEqual(formula_record["leaderboard"]["rank"], 2)
        self.assertEqual(formula_record["hall_of_fame"]["rank"], 2)
        self.assertEqual(review.preview["counts"]["leaderboard_positions_assigned"], 2)
        self.assertEqual(review.preview["counts"]["hall_of_fame_positions_assigned"], 2)

    def test_admin_upload_requires_superuser_and_confirms_only_once(self):
        review, reviewer = self.create_review()
        self.client.force_login(reviewer)
        response = self.client.post(reverse("admin:registry_legacydataimport_confirm", args=(review.pk,)))
        self.assertRedirects(response, reverse("admin:registry_legacydataimport_change", args=(review.pk,)))
        review.refresh_from_db()
        self.assertEqual(review.status, LegacyDataImport.Status.IMPORTED)
        self.assertEqual(LegacyRunSubmission.objects.filter(status="approved").count(), 4)

        response = self.client.post(reverse("admin:registry_legacydataimport_confirm", args=(review.pk,)))
        self.assertRedirects(response, reverse("admin:registry_legacydataimport_change", args=(review.pk,)))
        self.assertEqual(LegacyRun.objects.count(), 3)

    def test_admin_upload_builds_preview_without_importing(self):
        reviewer = Participant.objects.create_superuser(
            email="uploader@example.com", nickname="LegacyUploader", password="valid-test-password"
        )
        self.client.force_login(reviewer)
        response = self.client.post(reverse("admin:registry_legacydataimport_upload"), {
            "legacy_leaderboard": self.upload("leaderboard.csv", [
                "1,Active Racer,100,,12,0,0,2,3,10.5,https://twitch.tv/ignored",
            ]),
            "legacy_hall_of_fame": self.upload("hall.csv", [
                "1,Active Racer,250,,20,0,0,5,8,24.5,https://twitch.tv/ignored",
            ]),
        })

        review = LegacyDataImport.objects.get()
        self.assertRedirects(
            response, reverse("admin:registry_legacydataimport_change", args=(review.pk,))
        )
        self.assertEqual(review.status, LegacyDataImport.Status.PREVIEW)
        self.assertEqual(LegacyRun.objects.count(), 0)
        self.assertNotIn("twitch.tv", str(review.preview))

    def test_admin_changelist_offers_import_action(self):
        reviewer = Participant.objects.create_superuser(
            email="list@example.com", nickname="LegacyListAdmin", password="valid-test-password"
        )
        self.client.force_login(reviewer)

        response = self.client.get(reverse("admin:registry_legacydataimport_changelist"))

        self.assertContains(response, "Import legacy data")
        self.assertContains(response, reverse("admin:registry_legacydataimport_upload"))

    def test_non_superuser_cannot_open_import_upload(self):
        participant = Participant.objects.create_user(
            email="participant@example.com", nickname="Participant", password="valid-test-password"
        )
        self.client.force_login(participant)
        response = self.client.get(reverse("admin:registry_legacydataimport_upload"))
        self.assertEqual(response.status_code, 302)

    def test_legacy_ranking_sources_use_current_and_best_records(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        base = {
            "lifecycles": [],
            "selection": "all",
            "limit": 500,
        }

        leaderboard = build_ranking_table({
            **base, "source": "legacy_leaderboard", "ordering": "source_rank",
        })
        hall = build_ranking_table({
            **base, "source": "legacy_hall_of_fame", "ordering": "weighted_completion",
        })

        self.assertEqual([entry["racer"] for entry in leaderboard], ["Active Racer", "Second Racer"])
        self.assertEqual(leaderboard[0]["kills"], 100)
        self.assertIsNone(leaderboard[0]["run"])
        self.assertEqual(leaderboard[0]["legacy_run"].normalized_legacy_name, "active racer")
        self.assertEqual(hall[0]["racer"], "Active Racer")
        self.assertEqual(hall[0]["kills"], 250)
        imported_submission = hall[0]["legacy_run"].best_submission
        self.assertEqual(
            hall[0]["verified_at"],
            imported_submission.import_review.imported_at,
        )

    def test_legacy_verified_column_is_labelled_last_approved(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        block = PageBlock.objects.get(
            section__page__public_path="legacyhalloffame",
            block_type=PageBlock.BlockType.RANKING_TABLE,
        )
        config = dict(block.ranking_config)
        config["columns"] = [*config["columns"], "verified"]
        block.ranking_config = config
        block.save(update_fields=("ranking_config",))

        response = self.client.get("/legacyhalloffame/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Last approved")
        self.assertNotContains(response, "Last verified")
        self.assertNotContains(response, "Not recorded")

    def test_legacy_pages_render_when_survivor_names_are_empty(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)

        hall_block = PageBlock.objects.get(
            section__page__public_path="legacyhalloffame",
            block_type=PageBlock.BlockType.RANKING_TABLE,
        )
        leaderboard_page = Page.objects.create(
            title="Legacy Leaderboard",
            public_path="legacyleaderboard",
            is_published=True,
        )
        leaderboard_section = PageSection.objects.create(
            page=leaderboard_page,
            name="Legacy rankings",
            position=0,
        )
        leaderboard_config = dict(hall_block.ranking_config)
        leaderboard_config["source"] = "legacy_leaderboard"
        PageBlock.objects.create(
            section=leaderboard_section,
            position=0,
            block_type=PageBlock.BlockType.RANKING_TABLE,
            ranking_config=leaderboard_config,
        )

        for path in ("/legacyleaderboard/", "/legacyhalloffame/"):
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_HOST="127.0.0.1")

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Active Racer")
                self.assertNotContains(response, "/runs//")

    def test_participant_can_submit_legacy_run_claim(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="claimant@example.com", nickname="LegacyClaimant",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:claim_legacy_run", args=(legacy_run.pk,)),
            {"next": "/legacyleaderboard/"},
        )

        self.assertRedirects(
            response,
            "/legacyleaderboard/",
            fetch_redirect_response=False,
        )
        claim = LegacyRunClaim.objects.get(run=legacy_run, participant=participant)
        self.assertEqual(claim.status, LegacyRunClaim.Status.PENDING)

    def test_legacy_tables_hide_claim_column_after_approval(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="completed-claim@example.com",
            nickname="CompletedClaim",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        claim = LegacyRunClaim.objects.create(run=legacy_run, participant=participant)
        self.client.force_login(participant)

        response = self.client.get("/legacyhalloffame/", HTTP_HOST="127.0.0.1")
        self.assertContains(response, 'class="managed-ranking-claim"')

        claim.status = LegacyRunClaim.Status.APPROVED
        claim.save(update_fields=("status",))
        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        response = self.client.get("/legacyhalloffame/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="managed-ranking-claim"')
        self.assertNotContains(response, "data-legacy-claim-open")

    def test_admin_approves_legacy_claim_through_review_action(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="approved-claimant@example.com",
            nickname="ApprovedClaimant",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        claim = LegacyRunClaim.objects.create(run=legacy_run, participant=participant)
        self.client.force_login(reviewer)

        change_url = reverse("admin:registry_legacyrunclaim_change", args=(claim.pk,))
        response = self.client.get(change_url)
        self.assertContains(response, "Approve claim")
        self.assertContains(response, "Decline")
        self.assertNotContains(response, "Save and continue editing")

        response = self.client.post(
            reverse("admin:registry_legacyrunclaim_approve", args=(claim.pk,))
        )

        self.assertRedirects(response, change_url)
        claim.refresh_from_db()
        legacy_run.refresh_from_db()
        self.assertEqual(claim.status, LegacyRunClaim.Status.APPROVED)
        self.assertEqual(claim.reviewed_by, reviewer)
        self.assertIsNotNone(claim.reviewed_at)
        self.assertEqual(legacy_run.claimed_participant, participant)
        notification = participant.notifications.get(title="Legacy run claim approved")
        self.assertEqual(notification.destination, reverse("registry:account"))

    def test_admin_declines_legacy_claim_with_required_reason(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="declined-claimant@example.com",
            nickname="DeclinedClaimant",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        claim = LegacyRunClaim.objects.create(run=legacy_run, participant=participant)
        self.client.force_login(reviewer)
        decline_url = reverse("admin:registry_legacyrunclaim_decline", args=(claim.pk,))

        response = self.client.post(decline_url, {"reason": ""})
        self.assertRedirects(
            response, reverse("admin:registry_legacyrunclaim_change", args=(claim.pk,))
        )
        claim.refresh_from_db()
        self.assertEqual(claim.status, LegacyRunClaim.Status.PENDING)

        response = self.client.post(
            decline_url, {"reason": "The supplied identity could not be verified."}
        )

        self.assertRedirects(
            response, reverse("admin:registry_legacyrunclaim_change", args=(claim.pk,))
        )
        claim.refresh_from_db()
        legacy_run.refresh_from_db()
        self.assertEqual(claim.status, LegacyRunClaim.Status.DECLINED)
        self.assertEqual(claim.reviewed_by, reviewer)
        self.assertEqual(claim.review_note, "The supplied identity could not be verified.")
        self.assertIsNone(legacy_run.claimed_participant)
        notification = participant.notifications.get(title="Legacy run claim declined")
        self.assertIn("could not be verified", notification.message)

    def test_dashboard_shows_legacy_claim_state_and_linked_results(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="dashboard-claimant@example.com",
            nickname="DashboardClaimant",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        claim = LegacyRunClaim.objects.create(run=legacy_run, participant=participant)
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Legacy Rat Race")
        self.assertContains(response, "Claim awaiting review")
        self.assertContains(response, "Active Racer")

        claim.status = LegacyRunClaim.Status.DECLINED
        claim.review_note = "The supplied evidence did not match."
        claim.save(update_fields=("status", "review_note"))
        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Claim not approved")
        self.assertContains(response, "The supplied evidence did not match.")

        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Historical racer")
        self.assertContains(response, "Legacy Leaderboard")
        self.assertContains(response, "100")
        self.assertContains(response, "Active")
        self.assertNotContains(response, "Legacy Hall of Fame")
        self.assertContains(response, "separate from verified Stable runs")
        self.assertLess(
            response.content.index(b"Awaiting Review"),
            response.content.index(b"Unstable archive"),
        )

        legacy_run.lifecycle = LegacyRun.Lifecycle.INACTIVE
        legacy_run.save(update_fields=("lifecycle", "updated_at"))
        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Legacy Hall of Fame")
        self.assertContains(response, "250")
        self.assertContains(response, "Inactive")
        self.assertNotContains(response, "Legacy Leaderboard")

    def test_survival_time_accepts_full_and_word_formats(self):
        original, full, days = parse_survival_time("09:10:27:01")
        self.assertEqual(original, "09:10:27:01")
        self.assertEqual(full, "09:10:27:01")
        self.assertEqual(str(days), "3567.04167")

        original, full, days = parse_survival_time(
            "1 year 5 months 20 days 6 hours"
        )
        self.assertEqual(full, "01:05:20:06")
        self.assertEqual(str(days), "530.25000")

    def test_claimed_active_participant_submits_legacy_update(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="legacy-update@example.com",
            nickname="LegacyUpdater",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:submit_legacy_run"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submit a legacy update")
        self.assertContains(response, "YY:MM:DD:HH")

        response = self.client.post(reverse("registry:submit_legacy_run"), {
            "character_name": "Legacy Survivor",
            "zombie_kills": "500000",
            "survival_time": "1 year 5 months 20 days 6 hours",
            "maxed_skills": "35",
            "outposts_cleared": "13",
            "run_state": "dead",
            "manual_evidence_url": "https://www.twitch.tv/videos/123456789",
            "evidence_start_seconds": "60",
            "evidence_end_seconds": "600",
        })

        self.assertRedirects(response, reverse("registry:account"))
        submission = LegacyRunSubmission.objects.get(
            run=legacy_run, source=LegacyRunSubmission.Source.PARTICIPANT
        )
        self.assertEqual(submission.status, LegacyRunSubmission.Status.RECEIVED)
        self.assertEqual(submission.survival_time_full, "01:05:20:06")
        self.assertEqual(str(submission.survival_days), "530.25000")
        self.assertEqual(str(submission.challenge_progress), "75.00000")
        self.assertTrue(submission.reports_death)
        self.assertEqual(submission.evidence_start_seconds, 60)
        self.assertTrue(participant.notifications.filter(title="Legacy update received").exists())

        response = self.client.get(reverse("registry:submit_legacy_run"))
        self.assertRedirects(response, reverse("registry:account"))

    def test_legacy_update_requires_claim_active_run_and_vod(self):
        participant = Participant.objects.create_user(
            email="legacy-ineligible@example.com",
            nickname="LegacyIneligible",
            password="valid-test-password",
        )
        self.client.force_login(participant)
        self.assertRedirects(
            self.client.get(reverse("registry:submit_legacy_run")),
            reverse("registry:account"),
        )

        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        response = self.client.post(reverse("registry:submit_legacy_run"), {
            "character_name": "No Evidence",
            "zombie_kills": "100",
            "survival_time": "00:00:10:00",
            "maxed_skills": "1",
            "outposts_cleared": "1",
            "run_state": "alive",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a recent broadcast or enter the VOD URL")
        self.assertFalse(LegacyRunSubmission.objects.filter(source="participant").exists())

    def test_admin_approves_legacy_update_and_applies_death(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="legacy-approved-update@example.com",
            nickname="LegacyApprovedUpdate",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        submission = LegacyRunSubmission.objects.create(
            run=legacy_run,
            source=LegacyRunSubmission.Source.PARTICIPANT,
            submitted_by=participant,
            character_name="Final Survivor",
            zombie_kills=500000,
            survival_time_input="01:05:20:06",
            survival_time_full="01:05:20:06",
            survival_days="530.25000",
            outposts_cleared=13,
            maxed_skills=35,
            challenge_progress="75.00000",
            reports_death=True,
            evidence_url="https://www.youtube.com/watch?v=legacy",
        )
        self.client.force_login(reviewer)

        review_response = self.client.get(
            reverse("admin:registry_legacyrunsubmission_change", args=(submission.pk,))
        )
        self.assertContains(review_response, "Approve update")
        self.assertContains(review_response, "Final Survivor")
        self.assertContains(review_response, "01:05:20:06")
        self.assertContains(review_response, "youtube.com/watch?v=legacy")

        response = self.client.post(
            reverse("admin:registry_legacyrunsubmission_approve", args=(submission.pk,))
        )

        self.assertRedirects(
            response,
            reverse("admin:registry_legacyrunsubmission_change", args=(submission.pk,)),
        )
        submission.refresh_from_db()
        legacy_run.refresh_from_db()
        self.assertEqual(submission.status, LegacyRunSubmission.Status.APPROVED)
        self.assertEqual(submission.reviewed_by, reviewer)
        self.assertEqual(legacy_run.current_submission, submission)
        self.assertEqual(legacy_run.best_submission, submission)
        self.assertEqual(legacy_run.lifecycle, LegacyRun.Lifecycle.DECEASED)
        self.assertEqual(legacy_run.character_name, "Final Survivor")
        self.assertTrue(participant.notifications.filter(title="Legacy update approved").exists())

    def test_admin_declines_legacy_update_without_changing_run(self):
        review, reviewer = self.create_review()
        apply_legacy_import(review, reviewer)
        participant = Participant.objects.create_user(
            email="legacy-declined-update@example.com",
            nickname="LegacyDeclinedUpdate",
            password="valid-test-password",
        )
        legacy_run = LegacyRun.objects.get(normalized_legacy_name="active racer")
        legacy_run.claimed_participant = participant
        legacy_run.save(update_fields=("claimed_participant", "updated_at"))
        original_current = legacy_run.current_submission
        submission = LegacyRunSubmission.objects.create(
            run=legacy_run,
            source=LegacyRunSubmission.Source.PARTICIPANT,
            submitted_by=participant,
            character_name="Declined Survivor",
            evidence_url="https://www.twitch.tv/videos/declined",
        )
        self.client.force_login(reviewer)
        response = self.client.post(
            reverse("admin:registry_legacyrunsubmission_decline", args=(submission.pk,)),
            {"reason": "The values did not match the VOD."},
        )

        self.assertRedirects(
            response,
            reverse("admin:registry_legacyrunsubmission_change", args=(submission.pk,)),
        )
        submission.refresh_from_db()
        legacy_run.refresh_from_db()
        self.assertEqual(submission.status, LegacyRunSubmission.Status.DECLINED)
        self.assertEqual(submission.review_note, "The values did not match the VOD.")
        self.assertEqual(legacy_run.current_submission, original_current)
        self.assertTrue(participant.notifications.filter(title="Legacy update declined").exists())


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        turnstile_patcher = patch(
            "registry.views.validate_turnstile", return_value=True
        )
        self.turnstile = turnstile_patcher.start()
        self.addCleanup(turnstile_patcher.stop)

    def registration_data(self, **overrides):
        session = self.client.session
        session["registration_age_eligibility"] = {
            "checked_at": timezone.now().timestamp(),
            "policy_version": settings.AGE_ELIGIBILITY_POLICY_VERSION,
        }
        session.save()
        data = {
            "nickname": "Spiffo Fan",
            "email": "player@example.com",
            "password": "Local-test-password-482!",
            "password_confirmation": "Local-test-password-482!",
            "acknowledge_privacy": True,
            "registration_submission": "1",
        }
        data.update(overrides)
        return data

    def test_registration_page_loads(self):
        response = self.client.get(reverse("registry:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign Up")
        self.assertContains(
            response,
            "<title>The Great Spiffo&#x27;s Rat Race | Sign Up</title>",
            html=True,
        )
        self.assertContains(response, "Please enter your date of birth")
        self.assertContains(response, "Your date of birth is not stored")
        self.assertContains(response, 'type="date"')
        self.assertNotContains(response, "cf-turnstile")
        self.assertContains(response, "Already have an account?")
        self.assertContains(response, reverse("registry:login"))
        self.assertContains(response, reverse("registry:privacy"))
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, 'data-site-menu-toggle')
        self.assertContains(response, 'aria-controls="primary-menu"')
        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'autocomplete="bday"')
        self.assertContains(response, "data-privacy-dialog")
        self.assertContains(response, "Participant privacy notice")

    def test_eligible_date_of_birth_unlocks_single_registration_form(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": "1984-04-25"},
        )

        self.assertRedirects(response, reverse("registry:register"))
        form_page = self.client.get(reverse("registry:register"))
        self.assertContains(form_page, 'autocomplete="email"')
        self.assertContains(form_page, 'autocomplete="new-password"', count=2)
        self.assertContains(form_page, "cf-turnstile")
        self.assertContains(form_page, "Create account")
        self.assertNotContains(form_page, "I confirm that I am aged 18 or over")

    def test_registration_form_enables_validation_on_focus_loss(self):
        self.registration_data()
        form_page = self.client.get(reverse("registry:register"))

        self.assertContains(form_page, "data-registration-form")
        self.assertContains(
            form_page,
            f'data-validation-url="{reverse("registry:validate_registration_field")}"',
        )
        self.assertContains(form_page, "registry/registration_validation.js")
        self.assertContains(form_page, 'data-validation-for="nickname"')
        self.assertContains(form_page, 'data-validation-for="password_confirmation"')

    def test_registration_field_validation_reports_availability_and_policy(self):
        self.registration_data()
        Participant.objects.create_user(
            nickname="ReservedRacer",
            email="reserved@example.com",
            password="Local-test-password-482!",
        )
        validation_url = reverse("registry:validate_registration_field")

        nickname = self.client.post(
            validation_url,
            {"field": "nickname", "value": "reservedracer"},
        )
        self.assertFalse(nickname.json()["valid"])
        self.assertIn("already reserved", nickname.json()["errors"][0])

        email = self.client.post(
            validation_url,
            {"field": "email", "value": "RESERVED@example.com"},
        )
        self.assertFalse(email.json()["valid"])
        self.assertIn("already registered", email.json()["errors"][0])

        password = self.client.post(
            validation_url,
            {"field": "password", "value": "password"},
        )
        self.assertFalse(password.json()["valid"])
        self.assertTrue(password.json()["errors"])

        available = self.client.post(
            validation_url,
            {"field": "nickname", "value": "AvailableRacer"},
        )
        self.assertTrue(available.json()["valid"])
        self.assertEqual(available.json()["message"], "This nickname is available.")

    def test_registration_field_validation_requires_current_age_eligibility(self):
        response = self.client.post(
            reverse("registry:validate_registration_field"),
            {"field": "nickname", "value": "AvailableRacer"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Registration eligibility has expired.")

    def test_age_gate_redirect_survives_inherited_refresh_header(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": "1984-04-25"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("registry:register"))

        form_page = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="max-age=0"
        )

        self.assertContains(form_page, "Create account")
        self.assertNotContains(form_page, "Please enter your date of birth")

    def test_hard_refresh_clears_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="no-cache"
        )

        self.assertContains(response, "Please enter your date of birth")
        self.assertNotIn("registration_age_eligibility", self.client.session)

    def test_control_refresh_header_clears_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(
            reverse("registry:register"), HTTP_CACHE_CONTROL="max-age=0"
        )

        self.assertContains(response, "Please enter your date of birth")
        self.assertNotIn("registration_age_eligibility", self.client.session)

    def test_ordinary_refresh_preserves_temporary_age_eligibility(self):
        self.registration_data()

        response = self.client.get(reverse("registry:register"))

        self.assertContains(response, "Create account")
        self.assertIn("registration_age_eligibility", self.client.session)

    def test_home_introduces_challenge_and_links_to_signup(self):
        response = self.client.get(reverse("registry:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A survival challenge measured in stories")
        self.assertContains(response, "Join The Rat Race")
        self.assertContains(response, reverse("registry:register"))

    def test_branding_controls_public_sign_in_prompt(self):
        branding = SiteBranding.current()
        branding.sign_in_prompt = "Returning Survivor?"
        branding.save(update_fields=("sign_in_prompt",))

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, "Returning Survivor?")
        self.assertContains(response, "Sign In")
        self.assertNotContains(response, 'data-registration-form')
        self.assertContains(response, "Indie Stone Terms")
        self.assertContains(response, 'target="_blank"')

    def test_published_managed_pages_render_and_join_navigation_in_order(self):
        later = Page.objects.create(
            title="Challenge rules", public_path="media/rules", is_published=True,
        )
        earlier = Page.objects.create(
            title="About the challenge", public_path="about", is_published=True,
        )
        media = NavigationItem.objects.create(label="Media", position=20)
        NavigationItem.objects.create(label="Rules", page=later, parent=media, position=10)
        NavigationItem.objects.create(label="About", page=earlier, position=10)
        section = PageSection.objects.create(page=later, name="Rules", position=0)
        PageBlock.objects.create(
            section=section, position=0, block_type=PageBlock.BlockType.TEXT,
            text_role=PageBlock.TextRole.HEADING,
            content="How the challenge works",
        )

        response = self.client.get(later.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How the challenge works")
        self.assertContains(response, "| Challenge rules")
        self.assertContains(
            response,
            f'href="{later.get_absolute_url()}" aria-current="page"',
        )
        menu = response.content.decode().split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
        earlier_url = earlier.get_absolute_url()
        later_url = later.get_absolute_url()
        self.assertLess(menu.index(earlier_url), menu.index(later_url))
        self.assertContains(response, "Media")
        self.assertContains(response, "site-nav-submenu")
        self.assertContains(response, 'class="site-nav-group-toggle"')
        self.assertContains(response, 'aria-label="Show Media menu"')

    def test_unpublished_and_non_navigation_pages_are_not_public_navigation(self):
        unpublished = Page.objects.create(
            title="Draft", public_path="draft", is_published=False,
        )
        hidden = Page.objects.create(
            title="Direct link", public_path="direct", is_published=True,
        )
        NavigationItem.objects.create(label="Draft", page=unpublished)

        response = self.client.get(reverse("registry:home"))

        self.assertNotContains(
            response, unpublished.get_absolute_url()
        )
        self.assertNotContains(response, hidden.get_absolute_url())
        self.assertEqual(
            self.client.get(unpublished.get_absolute_url()).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(hidden.get_absolute_url()).status_code,
            200,
        )

    def test_home_managed_page_address_redirects_to_site_root(self):
        response = self.client.get(reverse("registry:legacy_page", args=("home",)))
        self.assertRedirects(response, reverse("registry:home"), status_code=301)

    def test_homepage_editorial_content_comes_from_managed_page(self):
        page = Page.objects.get(slug="home")
        section = page.sections.get(position=0)
        blocks = section.blocks.all()
        changes = {
            PageBlock.TextRole.EYEBROW: "Custom small heading",
            PageBlock.TextRole.HEADING: "Custom main heading",
            PageBlock.TextRole.PARAGRAPH: "Custom homepage introduction.",
        }
        for text_role, content in changes.items():
            block = blocks.get(block_type=PageBlock.BlockType.TEXT, text_role=text_role)
            block.content = content
            block.save(update_fields=("content",))
        join_action = blocks.get(destination=PageBlock.Destination.REGISTER)
        join_action.content = "Custom join action"
        join_action.save(update_fields=("content",))
        login_action = blocks.get(destination=PageBlock.Destination.LOGIN)
        login_action.content = "Custom returning-player action"
        login_action.save(update_fields=("content",))
        account_action = blocks.get(destination=PageBlock.Destination.ACCOUNT)
        account_action.content = "Custom account action"
        account_action.save(update_fields=("content",))
        card_group = blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        items = list(card_group.items.all())
        items[0].heading = "Custom first step"
        items[0].save()
        items[1].description = "Custom second description."
        items[1].save()
        items[2].description = "Custom third description."
        items[2].save()

        response = self.client.get(reverse("registry:home"))

        for expected in (
            "Custom small heading",
            "Custom main heading",
            "Custom homepage introduction.",
            "Custom join action",
            "Custom returning-player action",
            "Custom first step",
            "Custom second description.",
            "Custom third description.",
        ):
            self.assertContains(response, expected)
        self.assertNotContains(
            response, "A survival challenge measured in stories"
        )

    def test_login_error_is_clear_without_revealing_account_state(self):
        response = self.client.post(
            reverse("registry:login"),
            {"username": "unknown@example.com", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The email or password was not recognised, or this account is not yet active.",
        )
        self.assertContains(response, reverse("registry:resend"))

    def test_draft_privacy_notice_is_public(self):
        response = self.client.get(reverse("registry:privacy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant privacy notice")
        self.assertContains(response, "Draft for development review")
        self.assertContains(response, "Sentinel Tech Ltd")
        self.assertContains(response, "thegreatspiffo@machus.co.uk")
        self.assertContains(response, "Unverified registrations are deleted after 30 days")
        self.assertContains(response, "Routine security and email-delivery logs are kept for 90 days")
        self.assertContains(response, "We do not currently rely on consent")
        self.assertContains(response, "Former Rat Racer")
        self.assertContains(response, "Your UK data-protection rights")
        self.assertContains(response, "within one calendar month")
        self.assertContains(response, "https://ico.org.uk/make-a-complaint/")

    @override_settings(
        SITE_LEGAL_NAME="Configured Operator Ltd",
        SITE_COMPANY_NUMBER="12345678",
        SITE_REGISTERED_OFFICE="1 Test Street, Testville",
        SITE_PRIVACY_EMAIL="privacy@example.com",
        SITE_PUBLIC_URL="https://example.com",
        SITE_FULL_TITLE="Configured Challenge",
        SITE_SHORT_TITLE="Configured Race",
        SITE_TAGLINE="Configured tagline",
        SITE_WELCOME_MESSAGE="Configured welcome!",
        SITE_FORMER_PARTICIPANT_LABEL="Configured Former Player",
        SITE_DISCLAIMER="Configured disclaimer.",
    )
    def test_public_operator_identity_comes_from_configuration(self):
        SiteBranding.objects.all().delete()
        response = self.client.get(reverse("registry:privacy"))

        self.assertContains(response, "Configured Operator Ltd")
        self.assertContains(response, "12345678")
        self.assertContains(response, "1 Test Street, Testville")
        self.assertContains(response, "privacy@example.com")
        self.assertContains(response, "Configured Challenge")
        self.assertContains(response, "Configured tagline")
        self.assertContains(response, "Configured Former Player")
        self.assertContains(response, "Configured disclaimer.")
        self.assertNotContains(response, "Sentinel Tech Ltd")
        self.assertNotContains(response, "The Great Spiffo&#x27;s Rat Race")

    def test_database_branding_overrides_environment_defaults(self):
        SiteBranding.objects.update_or_create(
            pk=SiteBranding.SINGLETON_PK,
            defaults={
                "full_title": "Database Challenge",
                "short_title": "Database Race",
                "tagline": "Database tagline",
                "welcome_message": "Database welcome!",
                "former_participant_label": "Database Former Player",
                "disclaimer": "Database disclaimer.",
            },
        )

        response = self.client.get(reverse("registry:privacy"))

        self.assertContains(response, "Database Challenge")
        self.assertContains(response, "Database tagline")
        self.assertContains(response, "Database Former Player")
        self.assertContains(response, "Database disclaimer.")

    def test_participant_can_download_only_their_account_data(self):
        participant = Participant.objects.create_user(
            email="export@example.com",
            nickname="Export Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
            privacy_notice_acknowledged_at=timezone.now(),
            privacy_notice_version="draft-1",
            age_eligibility_confirmed_at=timezone.now(),
            age_policy_version="18-plus-v1",
        )
        StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.DISCORD,
            provider_identity="80351110224678912",
            channel_identity="80351110224678912",
            display_name="Nelly",
            channel_url="https://discord.com/users/80351110224678912",
            granted_scopes=["identify"],
            provider_metadata={"username": "nelly"},
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:download_my_data"))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(payload["participant"]["nickname"], "Export Test")
        self.assertEqual(payload["participant"]["email"], "export@example.com")
        self.assertNotContains(response, participant.password)
        self.assertNotIn("admin_notes", payload["participant"])
        self.assertNotIn("normalized_email", payload["participant"])
        self.assertEqual(payload["participant"]["age_policy_version"], "18-plus-v1")
        self.assertIsNotNone(
            payload["participant"]["age_eligibility_confirmed_at"]
        )
        self.assertEqual(
            payload["participant"]["connected_accounts"][0]["provider"],
            StreamingAccount.Provider.DISCORD,
        )
        self.assertEqual(
            payload["participant"]["connected_accounts"][0]["provider_identity"],
            "80351110224678912",
        )
        self.assertNotIn("encrypted_access_token", response.content.decode())

    def test_account_closure_requires_current_password(self):
        participant = Participant.objects.create_user(
            email="closure@example.com",
            nickname="Closure Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:account_closure"),
            {
                "current_password": "wrong-password",
                "note": "Please close this.",
                "confirm": True,
            },
        )

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "current password is incorrect")
        self.assertIsNone(participant.deletion_requested_at)

    def test_account_closure_request_enters_admin_review_queue(self):
        participant = Participant.objects.create_user(
            email="closure@example.com",
            nickname="Closure Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:account_closure"),
            {
                "current_password": "Local-test-password-482!",
                "note": "Please close this.",
                "confirm": True,
            },
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("registry:account_closure_received"))
        self.assertIsNotNone(participant.deletion_requested_at)
        self.assertEqual(participant.deletion_request_note, "Please close this.")
        self.assertTrue(participant.is_active)

    def test_registration_rejects_failed_human_verification(self):
        self.turnstile.return_value = False

        response = self.client.post(
            reverse("registry:register"), self.registration_data()
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Please complete the human verification", status_code=400
        )
        self.assertEqual(Participant.objects.count(), 0)

    @override_settings(
        RUNTIME_STATE_BACKEND="database",
        SECURE_SSL_REDIRECT=False,
        SIGNUP_RATE_LIMIT=1,
    )
    def test_signup_rate_limit_blocks_repeated_attempts(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(
                nickname="Another Player", email="another@example.com"
            ),
        )

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many signup attempts", status_code=429)
        self.assertEqual(Participant.objects.count(), 1)

    def test_valid_registration_creates_pending_participant(self):
        response = self.client.post(
            reverse("registry:register"), self.registration_data()
        )
        participant = Participant.objects.get()
        self.assertRedirects(response, reverse("registry:thanks"))
        self.assertEqual(participant.nickname, "Spiffo Fan")
        self.assertEqual(participant.status, Participant.Status.PENDING)
        self.assertIsNotNone(participant.verification_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(participant.email, mail.outbox[0].to)
        self.assertTrue(participant.check_password("Local-test-password-482!"))
        self.assertFalse(participant.is_active)

    def test_verification_link_marks_participant_verified(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        verification_url = re.search(
            r"http://testserver/verify/\S+", mail.outbox[0].body
        ).group(0)

        response = self.client.get(verification_url)

        participant = Participant.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email verified")
        self.assertEqual(participant.status, Participant.Status.VERIFIED)
        self.assertIsNotNone(participant.verified_at)
        self.assertTrue(participant.is_active)

    def test_verified_participant_can_login_with_email(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(reverse("registry:verify", kwargs={"token": create_verification_token(participant)}))
        self.assertTrue(self.client.login(email="player@example.com", password="Local-test-password-482!"))
        response = self.client.get(reverse("registry:account"))
        self.assertContains(response, "Spiffo Fan")

    def test_account_page_shows_profile_and_controls(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.login(
            email="player@example.com", password="Local-test-password-482!"
        )

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to the Rat Race!")
        self.assertContains(response, "Spiffo Fan")
        self.assertContains(response, reverse("registry:account_settings"))
        self.assertContains(
            response,
            reverse("registry:participant_profile", args=(participant.pk,)),
        )
        self.assertContains(response, "View profile")
        self.assertContains(response, 'aria-label="Breadcrumb"')
        self.assertContains(response, 'aria-current="page">')
        self.assertNotContains(response, reverse("registry:password_change"))
        self.assertContains(response, "Personal Best")
        self.assertContains(response, "Active Runs")
        self.assertContains(response, "Past Runs")
        self.assertContains(response, "Awaiting Review")
        self.assertContains(response, reverse("registry:logout"))
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, ">Administration<")
        self.assertNotContains(response, ">Admin Dashboard</a>")

    def test_staff_account_omits_administration_from_public_navigation(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        participant.refresh_from_db()
        participant.is_staff = True
        participant.save(update_fields=("is_staff",))
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Administration<")
        self.assertNotContains(response, "Challenge administration")
        self.assertContains(response, reverse("admin:index"))
        self.assertContains(response, ">Admin Dashboard</a>")
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'rel="noopener"')

    def test_account_settings_hub_contains_security_privacy_and_closure_actions(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account settings")
        self.assertContains(response, "player@example.com")
        self.assertContains(response, reverse("registry:password_change"))
        self.assertContains(response, reverse("registry:notifications"))
        self.assertContains(response, reverse("registry:download_my_data"))
        self.assertContains(response, reverse("registry:privacy"))
        self.assertContains(response, reverse("registry:account_closure"))
        self.assertContains(response, "Connected accounts")
        self.assertContains(response, "Discord")
        self.assertContains(response, "Twitch")
        self.assertContains(response, "YouTube")
        self.assertContains(response, 'aria-label="Breadcrumb"')
        self.assertContains(response, reverse("registry:account"))
        self.assertContains(response, "Settings")
        self.assertContains(response, 'aria-current="page"')

    def test_account_settings_shows_connected_streaming_channel(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
            channel_url="https://www.twitch.tv/spiffostreams",
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertContains(response, "SpiffoStreams")
        self.assertContains(response, "Connected")
        self.assertContains(response, "https://www.twitch.tv/spiffostreams")
        self.assertContains(response, "View channel")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_account_settings_offers_reconnect_for_lost_connection(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
            channel_url="https://www.twitch.tv/spiffostreams",
            status=StreamingAccount.Status.RECONNECT_REQUIRED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account_settings"))

        self.assertContains(response, ">Reconnect</a>")
        self.assertContains(response, ">Disconnect</button>")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.streaming._json_request", return_value={})
    def test_twitch_disconnect_removes_connection(self, revoke_request):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
            channel_url="https://www.twitch.tv/spiffostreams",
            encrypted_access_token=encrypt_token("twitch-access-secret"),
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:disconnect_twitch"))

        self.assertRedirects(response, reverse("registry:account_settings"))
        self.assertFalse(
            StreamingAccount.objects.filter(pk=account.pk).exists()
        )
        revoke_request.assert_called_once()

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_twitch_connect_starts_state_protected_authorization(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:connect_twitch"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://id.twitch.tv/oauth2/authorize?"))
        self.assertIn("response_type=code", response.url)
        self.assertIn("force_verify=true", response.url)
        self.assertIn(TWITCH_STATE_SESSION_KEY, self.client.session)

    @patch("registry.views.refresh_twitch_media")
    def test_revoked_twitch_credentials_require_reconnect(self, refresh_media):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-user-42",
            channel_identity="twitch-channel-42",
            display_name="SpiffoStreams",
        )
        refresh_media.side_effect = TwitchIntegrationError(
            "Twitch access has been revoked. Reconnect Twitch to restore access.",
            status=401,
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:refresh_twitch_media"))

        self.assertRedirects(response, reverse("registry:submit_run"))
        account.refresh_from_db()
        self.assertEqual(
            account.status,
            StreamingAccount.Status.RECONNECT_REQUIRED,
        )

    @patch("registry.views.refresh_youtube_media")
    def test_youtube_media_refresh_returns_provider_specific_options(self, refresh_media):
        participant = Participant.objects.create_user(
            email="youtube-streamer@example.com",
            nickname="YouTubeStreamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.YOUTUBE,
            provider_identity="google-user-42",
            channel_identity="youtube-channel-42",
            display_name="Spiffo Videos",
            channel_url="https://www.youtube.com/channel/youtube-channel-42",
        )
        media = StreamingMedia.objects.create(
            account=account,
            kind=StreamingMedia.Kind.VIDEO,
            provider_media_id="youtube-video-42",
            title="A Rat Race run",
            canonical_url="https://www.youtube.com/watch?v=youtube-video-42",
            published_at=timezone.now(),
        )
        refresh_media.return_value = (1, 0)
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:refresh_streaming_media"),
            {"provider": StreamingAccount.Provider.YOUTUBE},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["provider"], StreamingAccount.Provider.YOUTUBE)
        self.assertIn(str(media.id), [item["value"] for item in response.json()["videos"]])
        returned_media = next(
            item for item in response.json()["videos"] if item["value"] == str(media.id)
        )
        self.assertEqual(returned_media["title"], "A Rat Race run")
        self.assertEqual(returned_media["provider"], StreamingAccount.Provider.YOUTUBE)
        self.assertEqual(response.json()["clips"], [])

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.views.validate_twitch_token")
    @patch("registry.views.exchange_twitch_code")
    def test_twitch_callback_links_owned_channel_and_encrypts_tokens(
        self, exchange_code, validate_token
    ):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        session = self.client.session
        session[TWITCH_STATE_SESSION_KEY] = {
            "value": "safe-state",
            "created_at": timezone.now().timestamp(),
        }
        session.save()
        exchange_code.return_value = {
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "expires_in": 3600,
            "scope": [],
        }
        validate_token.return_value = {
            "client_id": "client-id",
            "user_id": "42",
            "login": "spiffostreams",
            "expires_in": 3600,
            "scopes": None,
        }

        response = self.client.get(
            reverse("registry:twitch_callback"),
            {"code": "authorization-code", "state": "safe-state"},
        )

        self.assertRedirects(response, reverse("registry:account_settings"))
        account = StreamingAccount.objects.get(participant=participant)
        self.assertEqual(account.display_name, "spiffostreams")
        self.assertEqual(account.granted_scopes, [])
        self.assertNotIn("access-secret", account.encrypted_access_token)
        self.assertNotIn("refresh-secret", account.encrypted_refresh_token)
        self.assertEqual(decrypt_token(account.encrypted_access_token), "access-secret")
        self.assertEqual(decrypt_token(account.encrypted_refresh_token), "refresh-secret")

    @override_settings(
        TWITCH_CLIENT_ID="client-id",
        TWITCH_CLIENT_SECRET="client-secret",
        TWITCH_REDIRECT_URI="http://testserver/account/streaming/twitch/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_twitch_callback_rejects_invalid_state_without_exchanging_code(self):
        participant = Participant.objects.create_user(
            email="streamer@example.com",
            nickname="Streamer",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        with patch("registry.views.exchange_twitch_code") as exchange_code:
            response = self.client.get(
                reverse("registry:twitch_callback"),
                {"code": "authorization-code", "state": "wrong-state"},
            )

        self.assertRedirects(response, reverse("registry:account_settings"))
        exchange_code.assert_not_called()
        self.assertFalse(StreamingAccount.objects.exists())

    @override_settings(
        DISCORD_CLIENT_ID="discord-client-id",
        DISCORD_CLIENT_SECRET="discord-client-secret",
        DISCORD_REDIRECT_URI="http://testserver/account/connections/discord/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_discord_connect_requests_only_identity_scope(self):
        participant = Participant.objects.create_user(
            email="discord@example.com",
            nickname="Discord User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:connect_discord"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("https://discord.com/oauth2/authorize?"))
        self.assertIn("scope=identify", response.url)
        self.assertIn(DISCORD_STATE_SESSION_KEY, self.client.session)

    @override_settings(
        DISCORD_CLIENT_ID="discord-client-id",
        DISCORD_CLIENT_SECRET="discord-client-secret",
        DISCORD_REDIRECT_URI="http://testserver/account/connections/discord/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.views.fetch_discord_identity")
    @patch("registry.views.exchange_discord_code")
    def test_discord_callback_links_identity_and_encrypts_tokens(
        self, exchange_code, fetch_identity
    ):
        participant = Participant.objects.create_user(
            email="discord@example.com",
            nickname="Discord User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        session = self.client.session
        session[DISCORD_STATE_SESSION_KEY] = {
            "value": "safe-state",
            "created_at": timezone.now().timestamp(),
        }
        session.save()
        exchange_code.return_value = {
            "access_token": "discord-access-secret",
            "refresh_token": "discord-refresh-secret",
            "expires_in": 604800,
            "scope": "identify",
        }
        fetch_identity.return_value = {
            "id": "80351110224678912",
            "username": "nelly",
            "global_name": "Nelly",
            "avatar": "avatar-hash",
        }

        response = self.client.get(
            reverse("registry:discord_callback"),
            {"code": "authorization-code", "state": "safe-state"},
        )

        self.assertRedirects(response, reverse("registry:account_settings"))
        account = StreamingAccount.objects.get(
            participant=participant,
            provider=StreamingAccount.Provider.DISCORD,
        )
        self.assertEqual(account.provider_identity, "80351110224678912")
        self.assertEqual(account.display_name, "Nelly")
        self.assertEqual(account.granted_scopes, ["identify"])
        self.assertEqual(account.provider_metadata["avatar"], "avatar-hash")
        self.assertEqual(
            decrypt_token(account.encrypted_access_token),
            "discord-access-secret",
        )

    @override_settings(
        DISCORD_CLIENT_ID="discord-client-id",
        DISCORD_CLIENT_SECRET="discord-client-secret",
        DISCORD_REDIRECT_URI="http://testserver/account/connections/discord/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.discord_integration._json_request", return_value={})
    def test_discord_disconnect_removes_connection(self, revoke_request):
        participant = Participant.objects.create_user(
            email="discord@example.com",
            nickname="Discord User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.DISCORD,
            provider_identity="80351110224678912",
            channel_identity="80351110224678912",
            display_name="Nelly",
            channel_url="https://discord.com/users/80351110224678912",
            encrypted_access_token=encrypt_token("discord-access-secret"),
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:disconnect_discord"))

        self.assertRedirects(response, reverse("registry:account_settings"))
        self.assertFalse(
            StreamingAccount.objects.filter(pk=account.pk).exists()
        )
        revoke_request.assert_called_once()

    def test_avatar_upload_is_quarantined_when_moderation_is_not_configured(self):
        participant = Participant.objects.create_user(
            email="avatar@example.com", nickname="Avatar User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        image_buffer = BytesIO()
        Image.new("RGB", (300, 200), "orange").save(image_buffer, "PNG")
        upload = SimpleUploadedFile("avatar.png", image_buffer.getvalue(), content_type="image/png")

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(
                MEDIA_ROOT=media_root,
                AVATAR_QUARANTINE_ROOT=quarantine_root,
                OPENAI_API_KEY="",
            ):
                response = self.client.post(reverse("registry:upload_avatar"), {"avatar": upload})
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.PENDING)
                self.assertFalse(participant.avatar)
                self.assertTrue((Path(quarantine_root) / participant.avatar_review_path).is_file())

    def test_pending_replacement_keeps_approved_avatar_visible_until_approval(self):
        old_image = BytesIO()
        Image.new("RGB", (512, 512), "green").save(old_image, "WEBP")
        replacement = BytesIO()
        Image.new("RGB", (300, 300), "blue").save(replacement, "PNG")

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(
                MEDIA_ROOT=media_root,
                AVATAR_QUARANTINE_ROOT=quarantine_root,
                OPENAI_API_KEY="",
            ):
                participant = Participant.objects.create_user(
                    email="replacement-avatar@example.com", nickname="Replacement Avatar",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.APPROVED,
                )
                participant.avatar.save(
                    "existing.webp",
                    SimpleUploadedFile("existing.webp", old_image.getvalue(), content_type="image/webp"),
                )
                original_name = participant.avatar.name
                original_url = participant.avatar.url
                self.client.force_login(participant)

                response = self.client.post(
                    reverse("registry:upload_avatar"),
                    {"avatar": SimpleUploadedFile("replacement.png", replacement.getvalue(), content_type="image/png")},
                )
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.PENDING)
                self.assertEqual(participant.avatar.name, original_name)
                self.assertTrue((Path(media_root) / original_name).is_file())
                self.assertContains(self.client.get(reverse("registry:account")), original_url)

                reject_pending_avatar(participant)
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.REJECTED)
                self.assertEqual(participant.avatar.name, original_name)
                self.assertContains(self.client.get(reverse("registry:account")), original_url)

                replacement.seek(0)
                self.client.post(
                    reverse("registry:upload_avatar"),
                    {"avatar": SimpleUploadedFile("replacement.png", replacement.getvalue(), content_type="image/png")},
                )
                participant.refresh_from_db()
                self.assertTrue(approve_pending_avatar(participant))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertNotEqual(participant.avatar.name, original_name)
                self.assertFalse((Path(media_root) / original_name).exists())

    @patch("registry.avatar_moderation.moderate_avatar", return_value=("approved", "Passed automatic moderation."))
    def test_approved_avatar_is_reencoded_and_published(self, moderate):
        participant = Participant.objects.create_user(
            email="approved-avatar@example.com", nickname="Approved Avatar",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        image_buffer = BytesIO()
        Image.new("RGB", (200, 300), "green").save(image_buffer, "JPEG")
        upload = SimpleUploadedFile("avatar.jpg", image_buffer.getvalue(), content_type="image/jpeg")

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                response = self.client.post(reverse("registry:upload_avatar"), {"avatar": upload})
                self.assertRedirects(response, reverse("registry:account"))
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertTrue(participant.avatar.name.endswith(".webp"))
                with Image.open(Path(media_root) / participant.avatar.name) as saved:
                    self.assertEqual(saved.size, (512, 512))
        moderate.assert_called_once()

    def test_admin_can_approve_or_decline_avatar_beside_preview(self):
        administrator = Participant.objects.create_superuser(
            email="avatar-admin@example.com", nickname="Avatar Admin",
            password="Local-test-password-482!",
        )
        self.client.force_login(administrator)
        image_buffer = BytesIO()
        Image.new("RGB", (512, 512), "purple").save(image_buffer, "WEBP")
        image_bytes = image_buffer.getvalue()

        with tempfile.TemporaryDirectory() as media_root, tempfile.TemporaryDirectory() as quarantine_root:
            with self.settings(MEDIA_ROOT=media_root, AVATAR_QUARANTINE_ROOT=quarantine_root):
                participant = Participant.objects.create_user(
                    email="approve-me@example.com", nickname="Approve Me",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.PENDING,
                    avatar_review_path="approve.webp",
                )
                (Path(quarantine_root) / "approve.webp").write_bytes(image_bytes)
                change_url = reverse("admin:registry_participant_change", args=(participant.pk,))
                page = self.client.get(change_url)
                self.assertContains(page, "Pending review")
                self.assertContains(page, "Approve")
                self.assertContains(page, "Decline")
                self.assertContains(page, 'name="avatar_status"')
                self.assertNotContains(page, '<select name="avatar_status"')

                response = self.client.post(reverse("admin:registry_participant_avatar_approve", args=(participant.pk,)))
                self.assertRedirects(response, change_url)
                participant.refresh_from_db()
                self.assertEqual(participant.avatar_status, Participant.AvatarStatus.APPROVED)
                self.assertTrue(participant.avatar)

                declined = Participant.objects.create_user(
                    email="decline-me@example.com", nickname="Decline Me",
                    password="Local-test-password-482!", is_active=True,
                    status=Participant.Status.VERIFIED,
                    avatar_status=Participant.AvatarStatus.PENDING,
                    avatar_review_path="decline.webp",
                )
                (Path(quarantine_root) / "decline.webp").write_bytes(image_bytes)
                response = self.client.post(reverse("admin:registry_participant_avatar_decline", args=(declined.pk,)))
                self.assertRedirects(response, reverse("admin:registry_participant_change", args=(declined.pk,)))
                declined.refresh_from_db()
                self.assertEqual(declined.avatar_status, Participant.AvatarStatus.REJECTED)
                self.assertFalse((Path(quarantine_root) / "decline.webp").exists())

    def test_account_dashboard_leaves_notifications_to_notification_menu(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        Notification.objects.create(
            recipient=participant,
            title="Submission received",
            message="Your first run update is waiting for review.",
            category=Notification.Category.SUBMISSION,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:account"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<h3>Notifications</h3>", html=True)
        self.assertContains(response, "Personal Best")
        self.assertContains(response, "Active Runs")
        self.assertContains(response, "Past Runs")
        self.assertContains(response, "Awaiting Review")
        self.assertContains(response, "data-dashboard-live")
        self.assertNotContains(response, "Unread notifications")

        fragment = self.client.get(reverse("registry:account_dashboard_fragment"))
        self.assertEqual(fragment.status_code, 200)
        self.assertEqual(fragment["Cache-Control"], "no-store")
        self.assertContains(fragment, "data-dashboard-live")
        self.assertContains(fragment, "Personal Best")
        self.assertNotContains(fragment, "account-dashboard-header")

    def test_participant_can_change_password_and_remains_logged_in(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        self.client.login(
            email="player@example.com", password="Local-test-password-482!"
        )

        response = self.client.post(
            reverse("registry:password_change"),
            {
                "old_password": "Local-test-password-482!",
                "new_password1": "Changed-local-password-951!",
                "new_password2": "Changed-local-password-951!",
            },
        )

        participant.refresh_from_db()
        self.assertRedirects(response, reverse("registry:password_change_done"))
        self.assertTrue(participant.check_password("Changed-local-password-951!"))
        self.assertFalse(participant.check_password("Local-test-password-482!"))
        self.assertEqual(self.client.get(reverse("registry:account")).status_code, 200)

    def test_logout_ends_participant_session(self):
        participant = Participant.objects.create_user(
            email="logout@example.com",
            nickname="Logout Test",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:logout"))

        self.assertRedirects(response, reverse("registry:home"))
        account_response = self.client.get(reverse("registry:account"))
        self.assertRedirects(
            account_response,
            f"{reverse('registry:login')}?next={reverse('registry:account')}",
        )

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("registry:login"))

        self.assertContains(response, "Sign In")
        self.assertContains(response, "Don&rsquo;t have an account?")
        self.assertContains(response, "Forgot your password?")
        self.assertContains(response, reverse("registry:password_reset"))

    def test_compact_sign_in_returns_json_and_preserves_safe_destination(self):
        participant = Participant.objects.create_user(
            email="compact@example.com", nickname="Compact User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        response = self.client.post(
            reverse("registry:login"),
            {"username": participant.email, "password": "Local-test-password-482!", "next": "/account/"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"signed_in": True, "redirect": "/account/"})

    def test_compact_sign_in_rejects_invalid_credentials_without_account_disclosure(self):
        response = self.client.post(
            reverse("registry:login"),
            {"username": "unknown@example.com", "password": "incorrect"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["signed_in"])
        self.assertIn("not recognised", response.json()["error"])

    def test_registration_and_verification_create_durable_notifications(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.assertTrue(participant.notifications.filter(title="Registration received").exists())

        self.client.get(reverse("registry:verify", kwargs={"token": create_verification_token(participant)}))

        self.assertTrue(participant.notifications.filter(title="Account verified").exists())

    def test_notification_panel_history_and_read_tracking(self):
        participant = Participant.objects.create_user(
            email="notify@example.com", nickname="Notify User",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        notification = Notification.objects.create(
            recipient=participant,
            category=Notification.Category.SUBMISSION,
            title="Submission received",
            message="Your submission has been received.",
            destination=reverse("registry:account"),
        )
        self.client.force_login(participant)

        account_response = self.client.get(reverse("registry:account"))
        self.assertNotContains(account_response, "<h3>Notifications</h3>", html=True)
        self.assertContains(account_response, 'class="notification-count">1</span>')
        history_response = self.client.get(reverse("registry:notifications"))
        self.assertContains(history_response, "Your submission has been received.")

        opened = self.client.get(reverse("registry:open_notification", args=(notification.pk,)))
        self.assertRedirects(opened, reverse("registry:account"))
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_notification_summary_returns_authoritative_dropdown_state(self):
        participant = Participant.objects.create_user(
            email="notify-summary@example.com",
            nickname="Notify Summary",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        notification = Notification.objects.create(
            recipient=participant,
            title="Submission approved",
            message="Your submission has been approved.",
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:notification_summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        payload = response.json()
        self.assertEqual(payload["unread_count"], 1)
        self.assertEqual(payload["notifications"][0]["id"], str(notification.pk))
        self.assertEqual(
            payload["notifications"][0]["title"],
            "Submission approved",
        )
        self.assertEqual(
            payload["notifications"][0]["open_url"],
            reverse("registry:open_notification", args=(notification.pk,)),
        )

    def test_notification_stream_is_an_authenticated_event_stream(self):
        participant = Participant.objects.create_user(
            email="notify-stream@example.com",
            nickname="Notify Stream",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        async def read_ready_event():
            await self.async_client.aforce_login(participant)
            response = await self.async_client.get(
                reverse("registry:notification_stream")
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)
            self.assertEqual(response["Content-Type"], "text/event-stream")
            self.assertEqual(response["X-Accel-Buffering"], "no")
            try:
                return await anext(response.streaming_content)
            finally:
                await response.streaming_content.aclose()

        first_event = async_to_sync(read_ready_event)()
        self.assertEqual(first_event, b"event: ready\ndata: {}\n\n")

    def test_notification_stream_falls_back_safely_under_wsgi(self):
        participant = Participant.objects.create_user(
            email="notify-wsgi@example.com",
            nickname="Notify WSGI",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:notification_stream"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_participant_can_mark_all_notifications_read(self):
        participant = Participant.objects.create_user(
            email="read-all@example.com", nickname="Read All",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        Notification.objects.create(recipient=participant, title="First", message="First message")
        Notification.objects.create(recipient=participant, title="Second", message="Second message")
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:mark_notifications_read"))

        self.assertRedirects(response, reverse("registry:notifications"))
        self.assertFalse(participant.notifications.filter(read_at__isnull=True).exists())

    def test_notification_popup_can_mark_all_read_and_return_to_current_page(self):
        participant = Participant.objects.create_user(
            email="popup-read@example.com", nickname="Popup Read",
            password="Local-test-password-482!", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        Notification.objects.create(
            recipient=participant, title="Update", message="An update is ready."
        )
        self.client.force_login(participant)

        account_response = self.client.get(reverse("registry:account"))
        self.assertContains(account_response, "Mark all as read")
        response = self.client.post(
            reverse("registry:mark_notifications_read"),
            {"next": reverse("registry:account")},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "unread_count": 0})
        self.assertFalse(
            participant.notifications.filter(read_at__isnull=True).exists()
        )

    def test_authenticated_participant_is_redirected_away_from_auth_forms(self):
        participant = Participant.objects.create_user(
            email="signed-in@example.com",
            nickname="Signed In",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        login_response = self.client.get(reverse("registry:login"))
        signup_response = self.client.get(reverse("registry:register"))

        self.assertRedirects(login_response, reverse("registry:account"))
        self.assertRedirects(signup_response, reverse("registry:account"))

    def test_password_reset_changes_password_and_link_becomes_invalid(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        self.client.get(
            reverse(
                "registry:verify",
                kwargs={"token": create_verification_token(participant)},
            )
        )
        mail.outbox.clear()

        request_response = self.client.post(
            reverse("registry:password_reset"), {"email": "PLAYER@example.com"}
        )
        reset_url = re.search(
            r"http://testserver/password-reset/\S+", mail.outbox[0].body
        ).group(0)
        reset_response = self.client.post(
            reset_url,
            {
                "new_password1": "New-local-password-736!",
                "new_password2": "New-local-password-736!",
            },
        )

        participant.refresh_from_db()
        self.assertEqual(request_response.status_code, 200)
        self.assertContains(request_response, "Check your email")
        self.assertRedirects(
            reset_response, reverse("registry:password_reset_complete")
        )
        self.assertTrue(participant.check_password("New-local-password-736!"))
        self.assertFalse(participant.check_password("Local-test-password-482!"))
        reused_response = self.client.get(reset_url)
        self.assertEqual(reused_response.status_code, 400)
        self.assertContains(reused_response, "already been used", status_code=400)

    def test_password_reset_does_not_reveal_unknown_email(self):
        response = self.client.post(
            reverse("registry:password_reset"), {"email": "unknown@example.com"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If an active participant account exists")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_rejects_failed_human_verification(self):
        self.turnstile.return_value = False

        response = self.client.post(
            reverse("registry:password_reset"), {"email": "unknown@example.com"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Please complete the human verification", status_code=400
        )

    def test_promoted_participant_keeps_credentials_and_gains_staff_access(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        class AdminStub:
            def message_user(self, *args, **kwargs):
                pass

        promote_to_role(AdminStub(), None, Participant.objects.all(), "Moderator")
        participant = Participant.objects.get()
        self.assertTrue(participant.is_staff)
        self.assertTrue(participant.groups.filter(name="Moderator").exists())
        self.assertTrue(participant.check_password("Local-test-password-482!"))

    def test_staff_access_follows_staff_role_membership(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        moderator = Group.objects.create(name="Moderator")

        participant.groups.add(moderator)
        participant.refresh_from_db()
        self.assertTrue(participant.is_staff)

        participant.groups.remove(moderator)
        participant.refresh_from_db()
        self.assertFalse(participant.is_staff)

    def test_verification_link_can_be_reopened(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )
        self.client.get(verify_url)

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email verified")

    def test_invalid_verification_link_is_rejected(self):
        response = self.client.get(
            reverse("registry:verify", kwargs={"token": "not-a-valid-token"})
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "verification link is invalid", status_code=400)

    @override_settings(VERIFICATION_LINK_MAX_AGE=-1)
    def test_expired_verification_link_is_rejected(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )

        response = self.client.get(verify_url)

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "verification link has expired", status_code=400)
        self.assertEqual(participant.status, Participant.Status.PENDING)

    def test_disabled_registration_cannot_be_verified(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        participant.status = Participant.Status.DISABLED
        participant.save(update_fields=("status",))
        verify_url = reverse(
            "registry:verify",
            kwargs={"token": create_verification_token(participant)},
        )

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "registration is unavailable", status_code=403)

    def test_nickname_is_unique_ignoring_case(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(
                nickname="spiffo fan", email="another@example.com"
            ),
        )
        self.assertEqual(Participant.objects.count(), 1)
        self.assertContains(response, "nickname is already reserved")

    def test_former_rat_racer_nickname_is_reserved_for_anonymous_display(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(nickname="Former Rat Racer"),
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "nickname is reserved by the system")

    def test_email_is_unique_ignoring_case(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(nickname="Another Player", email="PLAYER@example.com"),
        )
        self.assertEqual(Participant.objects.count(), 1)
        self.assertContains(response, "email address is already registered")
        self.assertContains(response, "Resend verification")
        self.assertContains(response, reverse("registry:resend"))

    def test_password_error_reopens_security_step(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(password_confirmation="A-different-password-482!"),
        )

        self.assertContains(response, "The passwords do not match.")

    def test_privacy_notice_acknowledgement_is_required(self):
        response = self.client.post(
            reverse("registry:register"),
            self.registration_data(acknowledge_privacy=False),
        )
        self.assertEqual(Participant.objects.count(), 0)
        self.assertContains(response, "confirm that you have read the privacy notice")

    def test_registration_submission_requires_completed_age_gate(self):
        data = self.registration_data()
        session = self.client.session
        session.pop("registration_age_eligibility", None)
        session.save()

        response = self.client.post(
            reverse("registry:register"),
            data,
        )

        self.assertEqual(Participant.objects.count(), 0)
        self.assertRedirects(response, reverse("registry:register"))

    def test_underage_date_of_birth_does_not_unlock_registration(self):
        response = self.client.post(
            reverse("registry:register"),
            {"age_gate_submission": "1", "date_of_birth": timezone.now().date().isoformat()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "aged 18 or over", status_code=400)
        self.assertNotIn("registration_age_eligibility", self.client.session)

    def test_resend_reactivates_expired_registration(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        participant.status = Participant.Status.EXPIRED
        participant.save(update_fields=("status",))
        mail.outbox.clear()

        response = self.client.post(
            reverse("registry:resend"), {"email": "PLAYER@example.com"}
        )

        participant.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If a pending registration exists")
        self.assertEqual(participant.status, Participant.Status.PENDING)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_does_not_reveal_unknown_email(self):
        response = self.client.post(
            reverse("registry:resend"), {"email": "unknown@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "If a pending registration exists")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        RUNTIME_STATE_BACKEND="database",
        SECURE_SSL_REDIRECT=False,
        RESEND_EMAIL_RATE_LIMIT=1,
    )
    def test_resend_rate_limit_blocks_repeated_email_requests(self):
        first = self.client.post(
            reverse("registry:resend"), {"email": "unknown@example.com"}
        )
        second = self.client.post(
            reverse("registry:resend"), {"email": "UNKNOWN@example.com"}
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertContains(second, "Too many requests", status_code=429)

    def test_old_pending_registration_is_expired(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        participant = Participant.objects.get()
        Participant.objects.filter(id=participant.id).update(
            verification_sent_at=timezone.now() - timedelta(days=8)
        )
        output = StringIO()

        call_command("expire_pending_registrations", stdout=output)

        participant.refresh_from_db()
        self.assertEqual(participant.status, Participant.Status.EXPIRED)
        self.assertIn("Expired 1 registration", output.getvalue())

    def test_admin_requires_login_and_lists_participants(self):
        self.client.post(reverse("registry:register"), self.registration_data())
        admin_url = reverse("admin:registry_participant_changelist")
        anonymous_response = self.client.get(admin_url)
        self.assertEqual(anonymous_response.status_code, 302)

        user = get_user_model().objects.create_superuser(
            email="local-admin@example.com",
            nickname="Local Admin",
            password="test-password-only",
        )
        self.client.force_login(user)
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spiffo Fan")

    def test_admin_home_redirects_to_participants(self):
        user = get_user_model().objects.create_superuser(
            email="breadcrumb-admin@example.com",
            nickname="Breadcrumb Admin",
            password="test-password-only",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:index"))

        self.assertRedirects(
            response,
            reverse("admin:registry_participant_changelist"),
            fetch_redirect_response=False,
        )

    def test_challenge_admin_can_confirm_and_process_account_closure(self):
        admin_user = get_user_model().objects.create_superuser(
            email="closure-admin@example.com",
            nickname="Closure Admin",
            password="test-password-only",
        )
        closure_reference = uuid.uuid4()
        participant = Participant.objects.create_user(
            email="leaving@example.com",
            nickname="Leaving Player",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
            deletion_requested_at=timezone.now(),
            deletion_request_reference=closure_reference,
        )
        self.client.force_login(admin_user)
        admin_url = reverse("admin:registry_participant_changelist")
        selection = {
            "action": "process_account_closures",
            "_selected_action": str(participant.pk),
        }

        confirmation = self.client.post(admin_url, selection)

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Confirm account closure and redaction")
        self.assertContains(confirmation, "Leaving Player")
        self.assertContains(confirmation, "Former Rat Racer")
        self.assertTrue(Participant.objects.filter(pk=participant.pk).exists())

        processed = self.client.post(admin_url, {**selection, "confirm": "yes"})

        self.assertEqual(processed.status_code, 302)
        self.assertFalse(Participant.objects.filter(pk=participant.pk).exists())
        self.assertFalse(
            Participant.objects.filter(
                id="00000000-0000-0000-0000-000000000001"
            ).exists()
        )
        self.assertTrue(
            AccountClosureRecord.objects.filter(reference=closure_reference).exists()
        )

    def test_staff_account_is_not_eligible_for_closure_processing(self):
        admin_user = get_user_model().objects.create_superuser(
            email="closure-admin@example.com",
            nickname="Closure Admin",
            password="test-password-only",
        )
        staff_participant = Participant.objects.create_user(
            email="staff-leaving@example.com",
            nickname="Staff Leaving",
            password="Local-test-password-482!",
            is_active=True,
            is_staff=True,
            status=Participant.Status.VERIFIED,
            deletion_requested_at=timezone.now(),
            deletion_request_reference=uuid.uuid4(),
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:registry_participant_changelist"),
            {
                "action": "process_account_closures",
                "_selected_action": str(staff_participant.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No eligible account-closure requests")
        self.assertTrue(Participant.objects.filter(pk=staff_participant.pk).exists())

    def test_admin_app_landing_page_keeps_navigation_sidebar(self):
        user = get_user_model().objects.create_superuser(
            email="app-index-admin@example.com",
            nickname="App Index Admin",
            password="test-password-only",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin:app_list", kwargs={"app_label": "auth"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-filter"')
        self.assertContains(response, "Participant administration")
        self.assertContains(response, "Challenge configuration")
        self.assertContains(response, "Run moderation")
        self.assertContains(response, "Platform integrations")

    def test_registry_app_landing_redirects_to_first_permitted_group_model(self):
        user = get_user_model().objects.create_superuser(
            email="registry-index-admin@example.com",
            nickname="Registry Index Admin",
            password="test-password-only",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("admin:app_list", kwargs={"app_label": "registry"})
        )

        self.assertRedirects(
            response,
            reverse("admin:registry_participant_changelist"),
            fetch_redirect_response=False,
        )

    def test_csv_export_contains_selected_registration(self):
        self.client.post(reverse("registry:register"), self.registration_data())

        response = export_registrations(
            None, None, Participant.objects.all()
        )

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("nickname,email,status", content)
        self.assertIn("Spiffo Fan,player@example.com,pending", content)

    @override_settings(
        YOUTUBE_CLIENT_ID="youtube-client-id",
        YOUTUBE_CLIENT_SECRET="youtube-client-secret",
        YOUTUBE_REDIRECT_URI="http://testserver/account/streaming/youtube/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    def test_youtube_connect_starts_state_protected_authorization(self):
        participant = Participant.objects.create_user(
            email="youtube@example.com",
            nickname="YouTube User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)

        response = self.client.get(reverse("registry:connect_youtube"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        )
        self.assertIn("youtube.readonly", response.url)
        self.assertIn("access_type=offline", response.url)
        self.assertIn(YOUTUBE_STATE_SESSION_KEY, self.client.session)

    @override_settings(
        YOUTUBE_CLIENT_ID="youtube-client-id",
        YOUTUBE_CLIENT_SECRET="youtube-client-secret",
        YOUTUBE_REDIRECT_URI="http://testserver/account/streaming/youtube/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.views.fetch_youtube_channel")
    @patch("registry.views.fetch_google_identity")
    @patch("registry.views.exchange_youtube_code")
    def test_youtube_callback_links_owned_channel_and_encrypts_tokens(
        self, exchange_code, fetch_identity, fetch_channel
    ):
        participant = Participant.objects.create_user(
            email="youtube@example.com",
            nickname="YouTube User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        session = self.client.session
        session[YOUTUBE_STATE_SESSION_KEY] = {
            "value": "safe-state",
            "created_at": timezone.now().timestamp(),
        }
        session.save()
        exchange_code.return_value = {
            "access_token": "youtube-access-secret",
            "refresh_token": "youtube-refresh-secret",
            "expires_in": 3600,
            "scope": "openid https://www.googleapis.com/auth/youtube.readonly",
        }
        fetch_identity.return_value = {
            "sub": "google-sub-42",
            "email": "owner@example.com",
        }
        fetch_channel.return_value = {
            "id": "youtube-channel-42",
            "snippet": {"title": "Spiffo Videos"},
        }

        response = self.client.get(
            reverse("registry:youtube_callback"),
            {"code": "authorization-code", "state": "safe-state"},
        )

        self.assertRedirects(response, reverse("registry:account_settings"))
        account = StreamingAccount.objects.get(
            participant=participant,
            provider=StreamingAccount.Provider.YOUTUBE,
        )
        self.assertEqual(account.provider_identity, "google-sub-42")
        self.assertEqual(account.channel_identity, "youtube-channel-42")
        self.assertEqual(account.display_name, "Spiffo Videos")
        self.assertEqual(
            decrypt_token(account.encrypted_access_token),
            "youtube-access-secret",
        )
        self.assertEqual(
            decrypt_token(account.encrypted_refresh_token),
            "youtube-refresh-secret",
        )

    def test_participant_can_select_only_an_owned_connected_broadcast_channel(self):
        participant = Participant.objects.create_user(
            email="primary@example.com",
            nickname="Primary User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        twitch = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.TWITCH,
            provider_identity="twitch-primary",
            channel_identity="twitch-primary",
            display_name="Primary Twitch",
            channel_url="https://www.twitch.tv/primary",
        )
        discord = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.DISCORD,
            provider_identity="discord-primary",
            channel_identity="discord-primary",
            display_name="Primary Discord",
            channel_url="https://discord.com/users/primary",
        )
        self.client.force_login(participant)

        response = self.client.post(
            reverse("registry:set_primary_streaming_channel"),
            {"account_id": twitch.id},
        )
        self.assertRedirects(response, reverse("registry:account_settings"))
        participant.refresh_from_db()
        self.assertEqual(participant.primary_streaming_account, twitch)

        response = self.client.post(
            reverse("registry:set_primary_streaming_channel"),
            {"account_id": discord.id},
        )
        self.assertEqual(response.status_code, 404)
        participant.refresh_from_db()
        self.assertEqual(participant.primary_streaming_account, twitch)

    @override_settings(
        YOUTUBE_CLIENT_ID="youtube-client-id",
        YOUTUBE_CLIENT_SECRET="youtube-client-secret",
        YOUTUBE_REDIRECT_URI="http://testserver/account/streaming/youtube/callback/",
        STREAMING_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("ascii"),
    )
    @patch("registry.youtube_integration._json_request", return_value={})
    def test_youtube_disconnect_clears_primary_channel(self, revoke_request):
        participant = Participant.objects.create_user(
            email="youtube@example.com",
            nickname="YouTube User",
            password="Local-test-password-482!",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        account = StreamingAccount.objects.create(
            participant=participant,
            provider=StreamingAccount.Provider.YOUTUBE,
            provider_identity="google-sub-42",
            channel_identity="youtube-channel-42",
            display_name="Spiffo Videos",
            channel_url="https://www.youtube.com/channel/youtube-channel-42",
            encrypted_access_token=encrypt_token("youtube-access-secret"),
        )
        participant.primary_streaming_account = account
        participant.save(update_fields=("primary_streaming_account",))
        self.client.force_login(participant)

        response = self.client.post(reverse("registry:disconnect_youtube"))

        self.assertRedirects(response, reverse("registry:account_settings"))
        participant.refresh_from_db()
        self.assertIsNone(participant.primary_streaming_account)
        revoke_request.assert_called_once()
