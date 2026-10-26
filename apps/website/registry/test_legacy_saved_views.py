from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import Participant, LegacyRun, LegacyRunClaim, LegacySavedView, LegacyViewPreference, LegacyWorkspacePreference


class LegacySavedViewTests(TestCase):
    def setUp(self):
        self.staff = Participant.objects.create_user(email="legacy-tabs@example.com", nickname="Tabs", is_staff=True, is_active=True)
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=("view_legacyrun", "view_legacyrunclaim", "view_legacyrunsubmission")))
        self.client.force_login(self.staff)
        self.url = reverse("admin:registry_legacyrun_changelist")

    def post(self, action, **values):
        return self.client.post(self.url, {"saved_view_action": action, **values})

    def test_default_order_prioritises_claims_then_updates(self):
        response = self.client.get(self.url)
        self.assertEqual([pref.view.system_key for pref in response.context["saved_tabs"]][:2], ["claims", "updates"])
        self.assertEqual(response.context["selected_view"].system_key, "claims")

    def test_claim_tab_uses_claim_table_and_remembers_filters(self):
        view = LegacySavedView.objects.get(system_key="claims")
        response = self.client.get(self.url, {"view": view.pk, "q": "example"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historical record")
        self.assertEqual(response.context["cl"].model._meta.model_name, "legacyrunclaim")
        response = self.client.get(self.url)
        self.assertEqual(response.context["selected_view"], view)
        self.assertEqual(response.context["cl"].query, "example")
        self.assertEqual(LegacyWorkspacePreference.objects.get(user=self.staff).last_view, view)
        response = self.client.get(self.url, {"view": view.pk, "reset": "1"})
        self.assertEqual(response.context["cl"].query, "")
        self.assertEqual(response.context["cl"].params["view"], str(view.pk))
        self.assertIn(f"view={view.pk}", response.context["cl"].get_query_string({"o": "1"}))
        response = self.client.get(self.url, {"view": view.pk, "_filters": "1", "status__exact": "approved"})
        self.assertEqual(response.context["cl"].model._meta.model_name, "legacyrunclaim")
        self.assertEqual(response.context["cl"].params["status__exact"], "approved")

    def test_personal_create_update_delete_and_shared_denial(self):
        self.assertEqual(self.post("create", name="My claims", workspace="claims", q="example").status_code, 302)
        view = LegacySavedView.objects.get(name="My claims")
        self.assertEqual(view.owner, self.staff)
        self.assertFalse(view.shared)
        response = self.client.get(self.url, {"view": view.pk})
        self.assertContains(response, "Historical record")
        self.assertEqual(self.post("update", view=view.pk, name="Renamed", workspace="claims", q="new").status_code, 302)
        view.refresh_from_db()
        self.assertEqual(view.filters["q"], "new")
        self.assertEqual(self.post("update", view=view.pk, name="Shared", workspace="claims", shared="on").status_code, 404)
        self.assertEqual(self.post("delete", view=view.pk).status_code, 302)
        self.assertFalse(LegacySavedView.objects.filter(pk=view.pk).exists())

    def test_permissions_prevent_imports_and_other_users_private_views(self):
        imports = LegacySavedView.objects.get(system_key="imports")
        self.assertEqual(self.client.get(self.url, {"view": imports.pk}).status_code, 404)
        self.assertEqual(self.post("create", name="Imports", workspace="imports").status_code, 404)
        other = Participant.objects.create_user(email="other-tabs@example.com", nickname="Other")
        private = LegacySavedView.objects.create(owner=other, name="Private", filters={"workspace": "claims"})
        self.assertEqual(self.client.get(self.url, {"view": private.pk}).status_code, 404)
        self.assertEqual(self.post("update", view=private.pk, name="Stolen", workspace="claims").status_code, 404)
        response = self.client.get(self.url)
        self.assertNotIn(imports.pk, [pref.view_id for pref in response.context["saved_tabs"]])

    def test_reorder_hide_restore_and_last_tab_guard(self):
        response = self.client.get(self.url)
        ids = [pref.view_id for pref in response.context["saved_tabs"]]
        self.assertEqual(self.post("reorder", order=list(reversed(ids))).status_code, 200)
        self.assertEqual(self.post("reorder", order=[ids[0], ids[0]]).status_code, 400)
        response = self.client.get(self.url)
        self.assertEqual([pref.view_id for pref in response.context["saved_tabs"]], list(reversed(ids)))
        for pk in ids:
            self.post("hide", view=pk)
        self.assertEqual(LegacyViewPreference.objects.filter(user=self.staff, hidden=False).count(), 1)
        self.post("show", view=ids[0])
        self.assertFalse(LegacyViewPreference.objects.get(user=self.staff, view_id=ids[0]).hidden)

    def test_shared_updates_reset_personal_overrides(self):
        self.staff.user_permissions.add(Permission.objects.get(codename="manage_shared_legacy_views"))
        view = LegacySavedView.objects.get(system_key="claims")
        self.client.get(self.url, {"view": view.pk, "q": "temporary"})
        response = self.post("update", view=view.pk, name="Claim review", workspace="claims", shared="on", status__exact="pending")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LegacyViewPreference.objects.get(user=self.staff, view=view).filters, {})
        self.assertEqual(self.post("delete", view=view.pk).status_code, 404)

    def test_direct_claim_list_keeps_pending_default_and_explicit_status_filters(self):
        run = LegacyRun.objects.create(source_key="claim-filter", legacy_participant_name="Filter Racer")
        pending = LegacyRunClaim.objects.create(run=run, participant=self.staff)
        other = Participant.objects.create_user(email="approved-filter@example.com", nickname="Approved Racer")
        approved = LegacyRunClaim.objects.create(run=run, participant=other, status="approved")
        url = reverse("admin:registry_legacyrunclaim_changelist")
        view = LegacySavedView.objects.get(system_key="claims")
        response = self.client.get(url)
        self.assertEqual(list(response.context["cl"].result_list), [pending])
        self.assertEqual(LegacyViewPreference.objects.get(user=self.staff, view=view).filters["status__exact"], "pending")
        response = self.client.get(self.url, {"view": view.pk})
        self.assertEqual(list(response.context["cl"].result_list), [pending])
        response = self.client.get(url, {"status__exact": "approved"})
        self.assertEqual(list(response.context["cl"].result_list), [approved])
        response = self.client.get(url, {"_filters": "1", "status__exact": ""})
        self.assertEqual(set(response.context["cl"].result_list), {pending, approved})
        response = self.client.get(url, {"reset": "1"})
        self.assertEqual(list(response.context["cl"].result_list), [pending])
