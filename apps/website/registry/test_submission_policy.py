from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ChallengeRun, Participant, RunSubmission, SubmissionAuditEntry, StreamingAccount
from .run_exports import decode_run_export
from .run_review import capture_preapproval_assessment, build_run_review
from .submission_approval import approve_submission, route_run, review_triggers, ApprovalBlocked
from .test_run_exports import make_export
from .vod_evidence import parse_vod_url


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SubmissionPolicyTests(TestCase):
    def setUp(self):
        self.owner = Participant.objects.create_user(email="policy@example.com", nickname="Policy", password="password", status="verified")
        self.staff = Participant.objects.create_superuser(email="audit@example.com", nickname="Auditor", password="password")
        self.events = [("session.started", {"character": {"displayName": "Test Survivor"}}), ("day.started", {"partial": False})]
        self.valid = patch("registry.vod_evidence.check_vod", return_value={"state": "valid", "reason": "Verified", "published_at": "2026-09-11T00:00:00Z"})
        self.valid.start()
        self.addCleanup(self.valid.stop)

    def submission(self, *, events=None, projection=None, generated=1784800100, url="https://www.twitch.tv/videos/123456"):
        raw = make_export(event_specs=events or self.events, projection=projection, generated_at=generated)
        decoded = decode_run_export(raw)
        run, _ = ChallengeRun.objects.get_or_create(run_id=decoded.run_id, defaults={
            "participant": self.owner, "export_format": decoded.format, "generated_at": decoded.generated_at})
        sub = RunSubmission.objects.create(run=run, submitter=self.owner, raw_export=raw,
            checksum=decoded.checksum, export_format=decoded.format, generated_at=decoded.generated_at,
            event_sequence=decoded.event_sequence, event_hash=decoded.event_hash,
            current_kills=decoded.current_kills, projection=decoded.projection, evidence_url=url)
        capture_preapproval_assessment(sub)
        return sub

    def baseline(self):
        sub = self.submission()
        approve_submission(sub.pk, self.staff)
        return sub

    def test_new_run_needs_human_then_clean_updates_advance_in_order(self):
        first = self.submission()
        second = self.submission(generated=1784800200)
        third = self.submission(generated=1784800300)
        route_run(first.run_id)
        self.assertEqual(RunSubmission.objects.filter(status="approved").count(), 0)
        approve_submission(first.pk, self.staff)
        route_run(first.run_id)
        second.refresh_from_db(); third.refresh_from_db()
        self.assertEqual(second.moderator_status, "Auto-Approved")
        self.assertEqual(third.baseline_submission_id, second.pk)
        self.assertIsNone(third.reviewed_by_id)
        self.assertEqual(third.get_status_display(), "Approved")
        self.assertEqual(build_run_review(second)["baseline"].pk, first.pk)

    def test_new_events_require_review_but_reviewed_events_do_not_repeat(self):
        self.baseline()
        for event in ("run.debug.enabled", "outpost.completed", "run.clock.repaired", "run.time.deviation", "run.reconciled"):
            with self.subTest(event=event):
                sub = self.submission(events=self.events+[(event, {})], generated=1784800200)
                self.assertTrue(review_triggers(sub))
                route_run(sub.run_id)
                sub.refresh_from_db(); self.assertEqual(sub.status, "received")
                sub.delete()
        sub = self.submission(events=self.events+[("run.debug.enabled", {})], generated=1784800200)
        approve_submission(sub.pk, self.staff)
        clean = self.submission(events=self.events+[("run.debug.enabled", {})], generated=1784800300)
        route_run(clean.run_id)
        clean.refresh_from_db(); self.assertEqual(clean.status, "approved")

    def test_mod_removal_even_if_restored_before_export_needs_review(self):
        self.baseline()
        sub = self.submission(events=self.events+[("session.started", {"removedMods": [{"modId": "test"}]})], generated=1784800200)
        self.assertIn("Mods changed", review_triggers(sub))

    def test_snapshot_mod_and_starting_changes_require_review(self):
        base = self.baseline()
        for key in ("activeMods", "recovery"):
            projection = deepcopy(base.projection); projection[key] = {"changed": True}
            sub = self.submission(projection=projection, generated=1784800200)
            self.assertTrue(review_triggers(sub)); sub.delete()
        projection = deepcopy(base.projection)
        projection["character"]["starting"]["displayName"] = "Changed"
        sub = self.submission(projection=projection, generated=1784800300)
        self.assertTrue(review_triggers(sub))

    def test_missing_evidence_blocks_following_updates(self):
        base = self.baseline()
        missing = self.submission(generated=1784800200, url="")
        later = self.submission(generated=1784800300)
        with patch("registry.vod_evidence.check_vod", return_value={"state":"missing", "reason":"Supply VOD"}):
            route_run(base.run_id)
        missing.refresh_from_db(); later.refresh_from_db()
        self.assertEqual(missing.status, "awaiting_evidence")
        self.assertEqual(later.status, "received")
        with self.assertRaises(ApprovalBlocked): approve_submission(later.pk, self.staff)

    def test_provider_failure_is_pending_not_missing_evidence(self):
        base = self.baseline(); sub = self.submission(generated=1784800200)
        with patch("registry.vod_evidence.check_vod", return_value={"state":"uncertain", "reason":"Provider unavailable"}):
            route_run(base.run_id)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "received")
        self.assertIn("Provider unavailable", sub.routing_reasons)

    def test_automatic_authority_failure_rolls_back(self):
        base = self.baseline(); sub = self.submission(generated=1784800200)
        with patch("registry.submission_approval.refresh_initial_run_authority", side_effect=RuntimeError("import failed")):
            with self.assertRaises(RuntimeError): route_run(base.run_id)
        sub.refresh_from_db(); base.run.refresh_from_db()
        self.assertEqual(sub.status, "received")
        self.assertEqual(base.run.approved_submission_id, base.pk)

    def test_changed_history_cannot_be_automatically_or_manually_approved(self):
        self.baseline()
        sub = self.submission(events=[self.events[0], ("day.started", {"partial":True})], generated=1784800200)
        route_run(sub.run_id)
        with self.assertRaises(ApprovalBlocked): approve_submission(sub.pk, self.staff)
        sub.refresh_from_db(); self.assertEqual(sub.status, "received")

    def test_audit_is_attributable_and_preserves_acceptance(self):
        base = self.baseline(); sub = self.submission(generated=1784800200); route_run(base.run_id)
        self.client.force_login(self.staff)
        page = self.client.get(reverse("admin:registry_challengerun_change", args=(sub.run_id,)) + "?tab=audits")
        self.assertContains(page, "Auto-Approved")
        url = reverse("admin:registry_runsubmission_audit", args=(sub.pk,))
        self.client.post(url, {"outcome":"passed", "evidence_intervals":"Twitch 123456, 00:10 to 00:20", "audit_note":"Matches export"})
        entry = SubmissionAuditEntry.objects.get()
        self.assertEqual(entry.reviewer, self.staff)
        sub.refresh_from_db(); self.assertEqual(sub.approval_method, "automatic")
        self.assertEqual(sub.status, "approved")
        self.client.force_login(self.owner)
        self.client.post(url, {"outcome":"action_required", "audit_note":"bad"})
        self.assertEqual(SubmissionAuditEntry.objects.count(), 1)

    def test_url_allowlist_and_embed(self):
        for url in ("https://twitch.tv.evil.test/videos/123", "https://twitch.tv/channel", "https://youtube.com/playlist?list=123", "https://twitch.tv@evil.test/videos/123", "javascript:alert(1)"):
            self.assertIsNone(parse_vod_url(url))
        self.assertEqual(parse_vod_url("https://youtu.be/abcdefghijk?t=3"), ("youtube", "abcdefghijk"))
        sub = self.baseline(); self.client.force_login(self.staff)
        page = self.client.get(reverse("admin:registry_runsubmission_change", args=(sub.pk,)))
        self.assertContains(page, "player.twitch.tv/")
        self.assertContains(page, "parent=testserver")

    def test_upload_executes_policy_after_commit(self):
        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("registry:submit_run"), {"run_export":make_export(), "manual_evidence_url":"https://twitch.tv/videos/123456"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RunSubmission.objects.get().routing_reasons, ["First approval for this run"])

    def test_missing_url_cannot_be_manually_approved(self):
        sub = self.submission(url="")
        with self.assertRaisesMessage(ApprovalBlocked, "Supply valid VOD"):
            approve_submission(sub.pk, self.staff)

    def test_evidence_correction_reassesses_and_advances_queue(self):
        self.baseline()
        sub = self.submission(generated=1784800200, url="")
        sub.status = "awaiting_evidence"; sub.save(update_fields=("status",))
        later = self.submission(generated=1784800300)
        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("registry:update_run_submission_evidence", args=(sub.pk,)),
                {"manual_evidence_url":"https://twitch.tv/videos/123456"})
        self.assertEqual(response.status_code, 302)
        sub.refresh_from_db(); later.refresh_from_db()
        self.assertEqual(sub.status, "approved")
        self.assertEqual(later.status, "approved")
        self.assertEqual(sub.evidence_revisions.count(), 1)

    def test_generic_admin_post_cannot_bypass_approval(self):
        sub = self.submission(); self.client.force_login(self.staff)
        response = self.client.post(reverse("admin:registry_runsubmission_change", args=(sub.pk,)), {"status":"approved"})
        self.assertEqual(response.status_code, 405)
        sub.refresh_from_db(); self.assertEqual(sub.status, "received")

    def test_audit_pass_requires_inspected_intervals_and_conclusion(self):
        sub = self.baseline(); self.client.force_login(self.staff)
        self.client.post(reverse("admin:registry_runsubmission_audit", args=(sub.pk,)), {"outcome":"passed"})
        self.assertFalse(SubmissionAuditEntry.objects.exists())

    def test_real_provider_check_distinguishes_bad_links_and_uncertainty(self):
        from .vod_evidence import _check_one_vod
        sub = self.submission(url="https://example.com/video")
        self.assertEqual(_check_one_vod(sub)["state"], "missing")
        sub.evidence_url = "https://twitch.tv/videos/123456"
        self.assertEqual(_check_one_vod(sub)["state"], "uncertain")
        StreamingAccount.objects.create(participant=self.owner, provider="twitch", channel_identity="123", provider_identity="123", status="connected")
        with patch("registry.streaming.get_valid_twitch_token", return_value="test-token"), patch("registry.streaming._twitch_api") as api:
            api.return_value = [{"user_id":"123", "type":"archive", "created_at":"2026-09-11T00:00:00Z"}]
            self.assertEqual(_check_one_vod(sub)["state"], "valid")
            api.return_value = []
            self.assertEqual(_check_one_vod(sub)["state"], "missing")
            from .streaming import TwitchIntegrationError
            api.side_effect = TwitchIntegrationError("Unavailable")
            self.assertEqual(_check_one_vod(sub)["state"], "uncertain")

    def test_stale_auto_evidence_cannot_be_reused_after_edit(self):
        self.baseline(); sub = self.submission(generated=1784800200)
        with patch("registry.submission_approval.approve_submission", side_effect=ApprovalBlocked("pause")):
            route_run(sub.run_id)
        sub.refresh_from_db()
        sub.evidence_start_seconds = 9; sub.save(update_fields=("evidence_start_seconds",))
        with self.assertRaises(ApprovalBlocked): approve_submission(sub.pk, automatic=True)

    def test_repeat_outpost_completion_requires_review(self):
        base = self.baseline()
        projection = deepcopy(base.projection)
        projection["outposts"] = [{"id": "test", "lifecycle": {"completionCount": 2}}]
        sub = self.submission(projection=projection, generated=1784800200)
        self.assertIn("Outpost completion evidence changed", review_triggers(sub))

    def test_existing_review_permission_grants_audit_access(self):
        self.owner.is_staff = True
        self.owner.save(update_fields=("is_staff",))
        self.owner.user_permissions.add(Permission.objects.get(codename="view_runsubmission"), Permission.objects.get(codename="view_challengerun"))
        self.client.force_login(self.owner)
        response = self.client.get(reverse("admin:registry_submissionaudit_changelist"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_additional_broadcast_uncertainty_blocks_automatic_evidence(self):
        self.valid.stop()
        from .vod_evidence import check_vod
        sub = self.submission()
        sub.evidence_clips = [{"kind": "video", "url": "https://youtu.be/abcdefghijk"}]
        with patch("registry.vod_evidence._check_one_vod", side_effect=[
            {"state": "valid", "reason": "Verified", "published_at": "2026-09-11T00:00:00Z"},
            {"state": "uncertain", "reason": "Check extra broadcast", "published_at": "2026-09-10T00:00:00Z"},
        ]):
            result = check_vod(sub)
        self.assertEqual(result["state"], "uncertain")
        self.assertEqual(result["published_at"], "2026-09-10T00:00:00Z")

    def test_run_tabs_keep_history_and_audits_scoped_to_run(self):
        sub = self.baseline()
        self.client.force_login(self.staff)
        url = reverse("admin:registry_challengerun_change", args=(sub.run_id,))
        overview = self.client.get(url)
        self.assertContains(overview, 'aria-label="This run"')
        self.assertNotContains(overview, "Uploaded run snapshots")
        history = self.client.get(url + "?tab=submissions")
        self.assertContains(history, "Uploaded run snapshots")
        self.assertContains(history, "run_tab=submissions")
        audits = self.client.get(url + "?tab=audits")
        self.assertContains(audits, "Submission audits for this run")
        self.assertContains(audits, "Not audited")
        self.assertNotContains(audits, "Current event ledger")

    def test_review_decision_returns_to_run_submissions_tab(self):
        sub = self.submission()
        self.client.force_login(self.staff)
        response = self.client.post(reverse("admin:registry_runsubmission_approve", args=(sub.pk,)) + "?return_to_run=1&run_tab=submissions")
        self.assertRedirects(response, reverse("admin:registry_challengerun_change", args=(sub.run_id,)) + "?tab=submissions")

    def test_later_pending_review_is_locked_until_reassessment(self):
        first = self.submission()
        second = self.submission(generated=1784800200)
        self.client.force_login(self.staff)
        run_url = reverse("admin:registry_challengerun_change", args=(first.run_id,)) + "?tab=submissions"
        later_url = reverse("admin:registry_runsubmission_change", args=(second.pk,))
        response = self.client.get(run_url)
        self.assertContains(response, "Waiting for earlier review")
        self.assertNotContains(response, later_url)
        self.assertRedirects(self.client.get(later_url), run_url)
        self.client.post(reverse("admin:registry_runsubmission_approve", args=(first.pk,)))
        second.refresh_from_db()
        self.assertEqual(second.moderator_status, "Auto-Approved")
        self.assertEqual(self.client.get(later_url).status_code, 200)

    def test_ledger_flags_new_review_events_and_changed_history(self):
        from .run_review import _event_rows
        event = {"sequence": 1, "event_type": "run.debug.enabled", "payload": {}}
        self.assertEqual(_event_rows([event])[0]["review_level"], "warning")
        self.assertEqual(_event_rows([event], [event])[0]["review_level"], "info")
        changed = {**event, "payload": {"changed": True}}
        self.assertEqual(_event_rows([changed], [event])[0]["review_level"], "danger")
        ordinary = {"sequence": 1, "event_type": "day.started", "payload": {}}
        self.assertEqual(_event_rows([ordinary])[0]["review_level"], "")

    def test_failed_approval_stays_on_review_with_error_and_context(self):
        sub = self.submission(url="")
        self.client.force_login(self.staff)
        query = "?return_to_run=1&run_tab=submissions"
        response = self.client.post(reverse("admin:registry_runsubmission_approve", args=(sub.pk,)) + query, follow=True)
        self.assertRedirects(response, reverse("admin:registry_runsubmission_change", args=(sub.pk,)) + query)
        self.assertContains(response, "Supply valid VOD evidence before approval.")
        sub.refresh_from_db()
        self.assertEqual(sub.status, RunSubmission.Status.RECEIVED)

    def test_blocked_approval_links_related_run_without_leaving_review(self):
        sub = self.submission()
        self.client.force_login(self.staff)
        with patch("registry.submission_approval.approve_submission", side_effect=ApprovalBlocked("Review the earlier death submission.", related_run=sub.run)):
            response = self.client.post(reverse("admin:registry_runsubmission_approve", args=(sub.pk,)), follow=True)
        self.assertContains(response, "Review the earlier death submission.")
        self.assertContains(response, reverse("admin:registry_challengerun_change", args=(sub.run_id,)) + "?tab=submissions")
        self.assertRedirects(response, reverse("admin:registry_runsubmission_change", args=(sub.pk,)))

    def test_optional_evidence_requires_first_review_then_automatically_advances(self):
        sub = self.submission(url="")
        from .models import ChallengeMode
        mode = ChallengeMode.objects.create(key="optional-evidence-test", display_name="Optional evidence", evidence_required=False)
        sub.challenge_mode = mode
        sub.save(update_fields=["challenge_mode"])
        sub.run.challenge_mode = mode
        sub.run.save(update_fields=["challenge_mode"])
        with self.assertRaises(ApprovalBlocked):
            approve_submission(sub.pk, automatic=True)
        approve_submission(sub.pk, self.staff)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "approved")
        sub.run.refresh_from_db()
        sub.run.challenge_mode = mode
        sub.run.save(update_fields=["challenge_mode"])
        second = self.submission(generated=1784800200, url="")
        third = self.submission(generated=1784800300, url="")
        with patch("registry.vod_evidence.check_vod", return_value={"state": "missing", "reason": "No URL or VOD provided"}), patch("registry.submission_approval.resolve_challenge_mode", return_value=mode):
            route_run(sub.run_id)
        second.refresh_from_db()
        third.refresh_from_db()
        self.assertEqual(second.approval_method, "automatic")
        self.assertEqual(third.approval_method, "automatic")
        self.assertEqual(third.baseline_submission_id, second.pk)

    def test_submission_form_requires_vod_for_required_mode(self):
        from .forms import RunSubmissionForm
        form = RunSubmissionForm(data={"run_export": make_export(event_specs=self.events)}, participant=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("manual_evidence_url", form.errors)

    def test_banner_uses_current_baseline_and_optional_evidence_policy(self):
        from .run_review import current_review_reasons
        from .models import ChallengeMode
        sub = self.submission(url="")
        mode = ChallengeMode.objects.create(key="banner-policy", display_name="Banner policy", evidence_required=False)
        sub.run.challenge_mode = mode
        sub.run.save(update_fields=["challenge_mode"])
        sub.routing_reasons = ["Supply a valid HTTPS Twitch or YouTube VOD link."]
        sub.save(update_fields=["routing_reasons"])
        self.assertEqual(current_review_reasons(sub), ["First approval for this run"])
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:registry_runsubmission_change", args=(sub.pk,)))
        self.assertContains(response, "First Approval")
        self.assertNotContains(response, "Supply a valid HTTPS Twitch or YouTube VOD link.")
        self.assertEqual(current_review_reasons(sub, {"baseline": sub}), [])
        mode.evidence_required = True
        mode.save(update_fields=["evidence_required"])
        self.assertIn("No URL or VOD provided", current_review_reasons(sub))


    def test_current_checks_ignore_obsolete_missing_evidence_warning(self):
        from .models import ChallengeMode
        from .run_review import current_review_summary
        sub = self.submission(url="")
        original_findings = deepcopy(sub.preapproval_findings)
        mode = ChallengeMode.objects.create(key="current-checks", display_name="Current checks", evidence_required=False)
        sub.run.challenge_mode = mode
        sub.run.save(update_fields=["challenge_mode"])
        self.assertEqual(current_review_summary(sub)["level"], "pass")
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:registry_challengerun_change", args=(sub.run_id,)), {"tab": "submissions"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All checks passed")
        sub.refresh_from_db()
        self.assertEqual(sub.preapproval_findings, original_findings)
        mode.evidence_required = True
        mode.save(update_fields=["evidence_required"])
        sub.run.refresh_from_db()
        self.assertEqual(current_review_summary(sub)["level"], "warning")


    def test_closed_runs_remain_viewable_but_have_no_review_work(self):
        from .run_saved_views import apply_work_filters
        from operations.run_moderation_reset import reset_run_moderation
        from django.db import transaction
        sub = self.submission()
        later = self.submission(generated=1784800200)
        self.client.force_login(self.staff)
        for lifecycle in ("invalidated",):
            sub.run.lifecycle_status = lifecycle
            sub.run.save(update_fields=["lifecycle_status"])
            with transaction.atomic():
                reset_run_moderation([sub.run_id])
            sub.run.refresh_from_db()
            self.assertEqual(sub.run.lifecycle_status, lifecycle)
            self.assertFalse(apply_work_filters(ChallengeRun.objects.all(), {"work": "review"}).exists())
            self.assertTrue(apply_work_filters(ChallengeRun.objects.all(), {}).exists())
            response = self.client.get(reverse("admin:registry_runsubmission_change", args=(later.pk,)))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Review unavailable: run " + lifecycle)
            self.assertNotContains(response, 'class="button run-review-approve"')
            with self.assertRaisesMessage(ApprovalBlocked, "This run is " + lifecycle):
                approve_submission(sub.pk, self.staff)


    def test_abandoned_run_can_be_reviewed_without_reactivation(self):
        from django.utils import timezone
        from .run_saved_views import apply_work_filters
        sub = self.submission()
        sub.run.lifecycle_status = "abandoned"
        sub.run.participant_deactivated_at = timezone.now()
        sub.run.save(update_fields=["lifecycle_status", "participant_deactivated_at"])
        self.assertTrue(apply_work_filters(ChallengeRun.objects.all(), {"work": "review"}).exists())
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:registry_runsubmission_change", args=(sub.pk,)))
        self.assertContains(response, 'class="button run-review-approve"')
        approve_submission(sub.pk, self.staff)
        sub.run.refresh_from_db()
        self.assertEqual(sub.run.lifecycle_status, "abandoned")
        self.assertEqual(sub.run.status, "official")
        self.assertIsNotNone(sub.run.participant_deactivated_at)
        self.assertEqual(sub.run.approved_submission_id, sub.pk)


    def test_event_comparison_shows_only_changed_fields_and_removed_events(self):
        from .run_review import event_field_changes, changed_event_details
        before = {"event_type": "day.started", "payload": {"value": 1, "same": True, "removed": None}}
        after = {"event_type": "day.started", "payload": {"value": 2, "same": True}}
        rows = event_field_changes(before, after)
        self.assertEqual([r["field"] for r in rows], ["payload.removed", "payload.value"])
        self.assertEqual(rows[0]["before"], "null")
        self.assertEqual(rows[0]["after"], "Not present")
        details = changed_event_details([before], [], [1])
        self.assertTrue(details[0]["removed"])
        self.assertEqual(details[0]["sequence"], 1)


    def test_queue_lock_after_approval_reports_saved_decision(self):
        from django.db import OperationalError
        sub = self.submission()
        self.client.force_login(self.staff)
        with patch("registry.submission_approval.route_run", side_effect=OperationalError("database is locked")):
            response = self.client.post(reverse("admin:registry_runsubmission_approve", args=(sub.pk,)), follow=True)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "approved")
        self.assertContains(response, "This submission was approved, but the database was busy")


    def test_debug_warning_is_visible_in_summary_and_becomes_reviewed(self):
        sub = self.submission(events=self.events + [("run.debug.enabled", {})])
        review = build_run_review(sub)
        self.assertEqual(review["severity"], "warning")
        self.assertTrue(any(f["title"] == "Debug used (human review required)" for f in review["findings"]))
        approve_submission(sub.pk, self.staff)
        sub.refresh_from_db()
        review = build_run_review(sub)
        self.assertTrue(any(f["level"] == "info" and f["title"] == "Debug used (covered by approval)" for f in review["findings"]))


    def test_invalid_stored_export_opens_with_blocking_finding(self):
        sub = self.submission()
        sub.raw_export = "invalid stored export"
        sub.save(update_fields=["raw_export"])
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:registry_runsubmission_change", args=(sub.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Export could not be validated")
        self.assertContains(response, "Comparison unavailable")
        self.assertContains(response, 'disabled title="Export validation failed"')
        with self.assertRaises(ApprovalBlocked):
            approve_submission(sub.pk, self.staff)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "received")
        self.assertEqual(sub.raw_export, "invalid stored export")


    def test_obsolete_red_assessment_does_not_block_current_valid_review(self):
        self.baseline()
        sub = self.submission(generated=1784800200)
        sub.preapproval_state = "red"
        sub.preapproval_findings = [{"level": "danger", "title": "Approved baseline could not be decoded", "message": "Historical failure"}]
        sub.save(update_fields=["preapproval_state", "preapproval_findings"])
        approve_submission(sub.pk, self.staff)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "approved")
        self.assertEqual(sub.preapproval_state, "red")


    def test_run_and_submission_history_include_existing_decisions(self):
        sub = self.submission()
        sub.status = "declined"
        sub.reviewed_by = self.staff
        from django.utils import timezone
        sub.reviewed_at = timezone.now()
        sub.review_note = "Invalid test export"
        sub.save()
        self.client.force_login(self.staff)
        for name, pk in (("challengerun", sub.run_id), ("runsubmission", sub.pk)):
            response = self.client.get(reverse("admin:registry_" + name + "_history", args=(pk,)))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid test export")
            self.assertContains(response, "Submission received")


    def test_approved_submission_has_audit_form_without_evidence_revisions(self):
        sub = self.baseline()
        self.client.force_login(self.staff)
        response = self.client.get(reverse("admin:registry_runsubmission_change", args=(sub.pk,)))
        self.assertContains(response, "Submit audit")
        self.assertContains(response, "data-audit-dialog")
