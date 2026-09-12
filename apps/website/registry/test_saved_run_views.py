from django.test import TestCase, override_settings
from django.urls import reverse
from .models import RunSavedView, RunViewPreference, RunWorkspacePreference, SubmissionAuditEntry, Participant
from . import test_submission_policy as policy


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SavedRunViewTests(TestCase):
    setUp = policy.SubmissionPolicyTests.setUp
    submission = policy.SubmissionPolicyTests.submission
    baseline = policy.SubmissionPolicyTests.baseline

    @property
    def url(self):
        return reverse("admin:registry_challengerun_changelist")

    def test_defaults_memory_and_hidden_fallback(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.context_data["selected_view"].system_key, "review")
        all_view = RunSavedView.objects.get(system_key="all")
        self.client.get(self.url, {"view": all_view.pk, "q": "Test"})
        response = self.client.get(self.url)
        self.assertEqual(response.context_data["selected_view"], all_view)
        self.assertEqual(response.context_data["search"], "Test")
        self.client.post(self.url, {"action": "hide", "view": all_view.pk})
        response = self.client.get(self.url)
        self.assertEqual(response.context_data["selected_view"].system_key, "review")

    def test_personal_ownership_shared_permissions_and_order(self):
        self.client.force_login(self.staff)
        self.client.post(self.url, {"action": "create", "name": "Team", "shared": "on", "vod": "closing"})
        view = RunSavedView.objects.get(name="Team")
        self.owner.is_staff = True
        self.owner.save()
        from django.contrib.auth.models import Permission
        self.owner.user_permissions.add(Permission.objects.get(codename="view_challengerun"))
        self.client.force_login(self.owner)
        page = self.client.get(self.url)
        self.assertContains(page, "Team")
        self.assertEqual(self.client.post(self.url, {"action": "update", "view": view.pk, "name": "Changed"}).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"action": "create", "name": "Bad", "shared": "on"}).status_code, 404)
        self.client.post(self.url, {"action": "create", "name": "Mine", "work": "evidence"})
        mine = RunSavedView.objects.get(name="Mine")
        before = RunViewPreference.objects.get(user=self.owner, view=mine).position
        self.client.post(self.url, {"action": "up", "view": mine.pk})
        self.assertLess(RunViewPreference.objects.get(user=self.owner, view=mine).position, before)
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(self.url), "Mine")
        self.assertEqual(self.client.post(self.url, {"action": "update", "view": mine.pk, "name": "Stolen"}).status_code, 404)

    def test_review_and_audit_views_use_submission_state(self):
        sub = self.submission()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).context_data["filtered_count"], 1)
        from .submission_approval import approve_submission
        approve_submission(sub.pk, self.staff)
        self.assertEqual(self.client.get(self.url).context_data["filtered_count"], 0)
        audit = RunSavedView.objects.get(system_key="audit")
        self.assertEqual(self.client.get(self.url, {"view": audit.pk}).context_data["filtered_count"], 1)
        SubmissionAuditEntry.objects.create(submission=sub, reviewer=self.staff, outcome="passed", note="Checked", evidence_intervals="0-30")
        self.assertEqual(self.client.get(self.url).context_data["filtered_count"], 0)
        self.submission(generated=1784800200)
        self.assertEqual(self.client.get(self.url, {"view": RunSavedView.objects.get(system_key="review").pk}).context_data["filtered_count"], 1)

    def test_vod_window_and_unknown_date(self):
        from django.utils import timezone
        from datetime import timedelta
        sub = self.baseline()
        sub.evidence_check = {"published_at": (timezone.now()-timedelta(days=6)).isoformat()}
        sub.save(update_fields=("evidence_check",))
        self.client.force_login(self.staff)
        all_view = RunSavedView.objects.get(system_key="all")
        self.assertEqual(self.client.get(self.url, {"view": all_view.pk, "vod": "closing"}).context_data["filtered_count"], 1)
        sub.evidence_check = {}; sub.save(update_fields=("evidence_check",))
        self.assertEqual(self.client.get(self.url).context_data["filtered_count"], 0)
        self.assertEqual(self.client.get(self.url, {"vod": "unknown"}).context_data["filtered_count"], 1)

    def test_delete_last_view_falls_back_and_foreign_view_cannot_be_selected(self):
        self.client.force_login(self.staff)
        self.client.post(self.url, {"action": "create", "name": "Disposable"})
        view = RunSavedView.objects.get(name="Disposable")
        self.client.get(self.url, {"view": view.pk})
        self.client.post(self.url, {"action": "delete", "view": view.pk})
        self.assertEqual(self.client.get(self.url).context_data["selected_view"].system_key, "review")
        foreign = RunSavedView.objects.create(owner=self.owner, name="Private")
        self.assertNotEqual(self.client.get(self.url, {"view": foreign.pk}).context_data["selected_view"], foreign)

    def test_additive_filters_match_either_value_and_remember_selection(self):
        sub = self.submission()
        self.client.force_login(self.staff)
        view = RunSavedView.objects.get(system_key="all")
        response = self.client.get(self.url, {"view": view.pk, "lifecycle_status": "active,completed"})
        self.assertContains(response, sub.run.run_id)
        remembered = self.client.get(self.url, {"view": view.pk})
        self.assertEqual(remembered.context_data["selected_lifecycle_status"], "active,completed")
        excluded = self.client.get(self.url, {"view": view.pk, "lifecycle_status": "deceased,completed"})
        self.assertNotContains(excluded, sub.run.run_id)


    def test_audit_filtered_row_opens_latest_approved_submission(self):
        sub = self.baseline()
        self.client.force_login(self.staff)
        all_view = RunSavedView.objects.get(system_key="all")
        response = self.client.get(self.url, {"view": all_view.pk, "audit": "unaudited"})
        expected = reverse("admin:registry_runsubmission_change", args=(sub.pk,)) + "?return_to_run=1&run_tab=audits"
        self.assertContains(response, expected.replace("&", "&amp;"))
